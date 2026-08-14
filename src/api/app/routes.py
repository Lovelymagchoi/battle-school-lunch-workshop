"""FastAPI 라우트: 학교 검색과 급식 조회."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
import httpx

from .config import Settings, get_settings
from .neis_client import NeisClient
from .schemas import MealSearchResponse, SchoolSearchResponse
from .services import MealService, SchoolService


router = APIRouter(prefix="/api")


def get_neis_client(settings: Settings = Depends(get_settings)) -> NeisClient:
    return NeisClient(settings)


@router.get("/health", tags=["operations"])
async def health() -> dict[str, str]:
    """liveness 확인용 엔드포인트."""
    return {"status": "ok"}


@router.get("/schools", response_model=SchoolSearchResponse, tags=["schools"])
async def search_schools(
    name: str = Query(..., min_length=1, description="학교 이름의 일부"),
    client: NeisClient = Depends(get_neis_client),
) -> SchoolSearchResponse:
    service = SchoolService(client)
    schools = await service.search_schools(name)
    return SchoolSearchResponse(schools=schools)


@router.get("/meals", response_model=MealSearchResponse, tags=["meals"])
async def search_meals(
    edu_office_code: str = Query(..., description="시도교육청코드 (ATPT_OFCDC_SC_CODE)"),
    school_code: str = Query(..., description="행정표준코드 (SD_SCHUL_CODE)"),
    from_date: date = Query(..., description="조회 시작일 (YYYY-MM-DD)"),
    to_date: date = Query(..., description="조회 종료일 (YYYY-MM-DD)"),
    client: NeisClient = Depends(get_neis_client),
) -> MealSearchResponse:
    service = MealService(client)
    meals = await service.get_meals(edu_office_code, school_code, from_date, to_date)
    return MealSearchResponse(
        school_code=school_code,
        edu_office_code=edu_office_code,
        from_date=from_date,
        to_date=to_date,
        meals=meals,
    )

@router.get("/timetable", tags=["timetable"])
async def search_timetable(
    edu_office_code: str = Query(...),
    school_code: str = Query(...),
    school_kind: str = Query(..., pattern="^(초등학교|중학교|고등학교)$"),
    grade: int = Query(..., ge=1, le=6),
    class_name: str = Query(..., min_length=1, max_length=3),
    date_ymd: date = Query(..., description="조회일 (YYYY-MM-DD)"),
    settings: Settings = Depends(get_settings),
) -> dict:
    endpoint = {"초등학교": "elsTimetable", "중학교": "misTimetable", "고등학교": "hisTimetable"}[school_kind]
    params = {
        "Key": settings.neis_api_key,
        "Type": "json",
        "pIndex": 1,
        "pSize": 100,
        "ATPT_OFCDC_SC_CODE": edu_office_code,
        "SD_SCHUL_CODE": school_code,
        "ALL_TI_YMD": date_ymd.strftime("%Y%m%d"),
        "GRADE": str(grade),
        "CLASS_NM": class_name,
    }
    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
        response = await client.get(f"{settings.neis_base_url}/hub/{endpoint}", params=params)
    response.raise_for_status()
    payload = response.json()
    root = payload.get(endpoint)
    if root is None:
        result = payload.get("RESULT", {})
        if result.get("CODE") == "INFO-200":
            return {"date": date_ymd, "periods": []}
        raise HTTPException(status_code=502, detail={"code": result.get("CODE", "NEIS_ERROR"), "message": result.get("MESSAGE", "시간표 조회에 실패했습니다.")})
    rows = root[1].get("row", []) if len(root) > 1 else []
    periods = [{"period": row.get("PERIO"), "subject": row.get("ITRT_CNTNT", ""), "teacher": row.get("TEACHER", "")} for row in rows]
    return {"date": date_ymd, "periods": periods}

