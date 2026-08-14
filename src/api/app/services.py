"""도메인 로직: NEIS 원시 데이터를 API 응답 모델로 변환한다."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import HTTPException, status

from .neis_client import NeisApiError, NeisClient
from .schemas import MealInfo, SchoolSummary

MAX_DATE_RANGE_DAYS = 31


def _parse_neis_date(value: object) -> date | None:
    """NEIS 날짜(YYYYMMDD 또는 ISO)를 안전하게 변환한다."""
    if value is None:
        return None
    raw = str(value).strip()
    if len(raw) == 8 and raw.isdigit():
        return date(int(raw[:4]), int(raw[4:6]), int(raw[6:8]))
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def _split_br(value: str | None) -> list[str]:
    """NEIS 응답의 `<br/>` 구분 문자열을 항목 배열로 분리한다."""
    if not value:
        return []
    return [item.strip() for item in value.split("<br/>") if item.strip()]


class SchoolService:
    def __init__(self, client: NeisClient) -> None:
        self._client = client

    async def search_schools(self, school_name: str) -> list[SchoolSummary]:
        try:
            rows = await self._client.get_school_info(school_name)
        except NeisApiError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={"code": exc.code, "message": exc.message},
            ) from exc

        return [
            SchoolSummary(
                school_code=row["SD_SCHUL_CODE"],
                edu_office_code=row["ATPT_OFCDC_SC_CODE"],
                school_name=row["SCHUL_NM"],
                edu_office_name=row["ATPT_OFCDC_SC_NM"],
                location_name=row.get("LCTN_SC_NM", ""),
                school_kind_name=row.get("SCHUL_KND_SC_NM", ""),
            )
            for row in rows
        ]


class MealService:
    def __init__(self, client: NeisClient) -> None:
        self._client = client

    async def get_meals(
        self,
        edu_office_code: str,
        school_code: str,
        from_date: date,
        to_date: date,
    ) -> list[MealInfo]:
        if to_date < from_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_RANGE", "message": "종료일은 시작일보다 빠를 수 없습니다."},
            )
        if (to_date - from_date) > timedelta(days=MAX_DATE_RANGE_DAYS - 1):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "RANGE_TOO_LONG",
                    "message": f"조회 기간은 최대 {MAX_DATE_RANGE_DAYS}일까지 가능합니다.",
                },
            )

        try:
            rows = await self._client.get_meal_service_diet_info(
                edu_office_code,
                school_code,
                from_date.strftime("%Y%m%d"),
                to_date.strftime("%Y%m%d"),
            )
        except NeisApiError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={"code": exc.code, "message": exc.message},
            ) from exc

        meals: list[MealInfo] = []
        for row in rows:
            meal_date = _parse_neis_date(row.get("MLSV_YMD"))
            if meal_date is None:
                continue
            meals.append(
                MealInfo(
                    meal_date=meal_date,
                    menu_items=_split_br(row.get("DDISH_NM")),
                    origin_items=_split_br(row.get("ORPLC_INFO")),
                    nutrition_items=_split_br(row.get("NTR_INFO")),
                    calorie_info=str(row["CAL_INFO"]) if row.get("CAL_INFO") is not None else None,
                    meal_headcount=str(row["MLSV_FGR"]) if row.get("MLSV_FGR") is not None else None,
                )
            )
        meals.sort(key=lambda meal: meal.meal_date)
        return meals
