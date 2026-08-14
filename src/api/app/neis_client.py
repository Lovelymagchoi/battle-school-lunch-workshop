"""NEIS 공개 API 호출을 담당하는 클라이언트.

`data/openapi.json`에 정의된 `/hub/schoolInfo`, `/hub/mealServiceDietInfo`
엔드포인트만 사용한다. NEIS_API_KEY는 서버 환경 변수로만 사용하며 응답에 노출하지 않는다.
"""

from __future__ import annotations

import httpx

from .config import Settings


class NeisApiError(Exception):
    """NEIS API가 오류 코드를 반환했을 때 발생한다."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"NEIS API error {code}: {message}")


class NeisClient:
    """httpx 기반 NEIS Open API 클라이언트."""

    # NEIS는 데이터가 없을 때 INFO-200을 반환한다. 이는 오류가 아니라 빈 결과로 취급한다.
    _NO_DATA_CODE = "INFO-200"
    _SUCCESS_CODE = "INFO-000"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def get_school_info(self, school_name: str) -> list[dict]:
        params = {
            "Key": self._settings.neis_api_key,
            "Type": "json",
            "pIndex": 1,
            "pSize": 100,
            "SCHUL_NM": school_name,
        }
        payload = await self._request("/hub/schoolInfo", params)
        return self._extract_rows(payload, "schoolInfo")

    async def get_meal_service_diet_info(
        self,
        edu_office_code: str,
        school_code: str,
        from_ymd: str,
        to_ymd: str,
    ) -> list[dict]:
        params = {
            "Key": self._settings.neis_api_key,
            "Type": "json",
            "pIndex": 1,
            "pSize": 100,
            "ATPT_OFCDC_SC_CODE": edu_office_code,
            "SD_SCHUL_CODE": school_code,
            "MMEAL_SC_CODE": "2",  # 중식 고정
            "MLSV_FROM_YMD": from_ymd,
            "MLSV_TO_YMD": to_ymd,
        }
        payload = await self._request("/hub/mealServiceDietInfo", params)
        return self._extract_rows(payload, "mealServiceDietInfo")

    async def _request(self, path: str, params: dict) -> dict:
        url = f"{self._settings.neis_base_url}{path}"
        async with httpx.AsyncClient(timeout=self._settings.request_timeout_seconds) as client:
            response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def _extract_rows(self, payload: dict, root_key: str) -> list[dict]:
        root = payload.get(root_key)

        if root is None:
            # NEIS는 결과가 없거나 파라미터 오류일 때 최상위 키 없이 RESULT 객체만 반환한다.
            result = payload.get("RESULT", {})
            code = result.get("CODE", self._NO_DATA_CODE)
            if code == self._NO_DATA_CODE:
                return []
            message = result.get("MESSAGE", "알 수 없는 오류")
            raise NeisApiError(code, message)

        head_section, *rest = root
        head_list = head_section.get("head", []) if isinstance(head_section, dict) else []
        result = next((entry["RESULT"] for entry in head_list if "RESULT" in entry), None)

        if result is not None:
            code = result.get("CODE", "")
            if code != self._SUCCESS_CODE:
                if code == self._NO_DATA_CODE:
                    return []
                raise NeisApiError(code, result.get("MESSAGE", "알 수 없는 오류"))

        if not rest:
            return []
        return rest[0].get("row", [])
