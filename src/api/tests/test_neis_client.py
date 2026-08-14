"""NeisClient 단위 테스트: 성공, 빈 결과(INFO-200), 오류 코드 처리를 검증한다."""

import httpx
import pytest
import respx

from app.config import Settings
from app.neis_client import NeisApiError, NeisClient


def make_client() -> NeisClient:
    settings = Settings(neis_api_key="test-key")
    return NeisClient(settings)


@pytest.mark.asyncio
@respx.mock
async def test_get_school_info_success():
    respx.get("https://open.neis.go.kr/hub/schoolInfo").mock(
        return_value=httpx.Response(
            200,
            json={
                "schoolInfo": [
                    {"head": [{"list_total_count": 1}, {"RESULT": {"CODE": "INFO-000", "MESSAGE": "정상"}}]},
                    {"row": [{"SD_SCHUL_CODE": "1", "ATPT_OFCDC_SC_CODE": "A", "SCHUL_NM": "서울고등학교"}]},
                ]
            },
        )
    )

    client = make_client()
    rows = await client.get_school_info("서울고")

    assert rows == [{"SD_SCHUL_CODE": "1", "ATPT_OFCDC_SC_CODE": "A", "SCHUL_NM": "서울고등학교"}]


@pytest.mark.asyncio
@respx.mock
async def test_get_school_info_no_data_returns_empty_list():
    respx.get("https://open.neis.go.kr/hub/schoolInfo").mock(
        return_value=httpx.Response(
            200,
            json={"RESULT": {"CODE": "INFO-200", "MESSAGE": "해당하는 데이터가 없습니다."}},
        )
    )

    client = make_client()
    rows = await client.get_school_info("존재하지않는학교")

    assert rows == []


@pytest.mark.asyncio
@respx.mock
async def test_get_meal_service_diet_info_raises_on_error_code():
    respx.get("https://open.neis.go.kr/hub/mealServiceDietInfo").mock(
        return_value=httpx.Response(
            200,
            json={"RESULT": {"CODE": "ERROR-300", "MESSAGE": "필수 파라미터 누락"}},
        )
    )

    client = make_client()

    with pytest.raises(NeisApiError) as exc_info:
        await client.get_meal_service_diet_info("A", "1", "20250501", "20250510")

    assert exc_info.value.code == "ERROR-300"
