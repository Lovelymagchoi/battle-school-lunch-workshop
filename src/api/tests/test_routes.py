"""API 엔드포인트 통합 테스트: 학교 검색, 급식 조회, 날짜 범위 검증."""

import httpx
import pytest
import respx
from httpx import ASGITransport

from app.main import app


@pytest.fixture
def client() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_health(client: httpx.AsyncClient):
    async with client as c:
        response = await c.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
@respx.mock
async def test_search_schools_returns_summary(client: httpx.AsyncClient):
    respx.get("https://open.neis.go.kr/hub/schoolInfo").mock(
        return_value=httpx.Response(
            200,
            json={
                "schoolInfo": [
                    {"head": [{"list_total_count": 1}, {"RESULT": {"CODE": "INFO-000", "MESSAGE": "정상"}}]},
                    {
                        "row": [
                            {
                                "SD_SCHUL_CODE": "7010569",
                                "ATPT_OFCDC_SC_CODE": "B10",
                                "SCHUL_NM": "서울고등학교",
                                "ATPT_OFCDC_SC_NM": "서울특별시교육청",
                                "LCTN_SC_NM": "서울특별시",
                                "SCHUL_KND_SC_NM": "고등학교",
                            }
                        ]
                    },
                ]
            },
        )
    )

    async with client as c:
        response = await c.get("/api/schools", params={"name": "서울고"})

    assert response.status_code == 200
    body = response.json()
    assert body["schools"][0]["school_name"] == "서울고등학교"
    assert body["schools"][0]["school_code"] == "7010569"


@pytest.mark.asyncio
@respx.mock
async def test_search_schools_empty_result(client: httpx.AsyncClient):
    respx.get("https://open.neis.go.kr/hub/schoolInfo").mock(
        return_value=httpx.Response(200, json={"RESULT": {"CODE": "INFO-200", "MESSAGE": "없음"}})
    )

    async with client as c:
        response = await c.get("/api/schools", params={"name": "없는학교"})

    assert response.status_code == 200
    assert response.json()["schools"] == []


@pytest.mark.asyncio
async def test_meals_invalid_range_returns_400(client: httpx.AsyncClient):
    async with client as c:
        response = await c.get(
            "/api/meals",
            params={
                "edu_office_code": "B10",
                "school_code": "7010569",
                "from_date": "2025-06-01",
                "to_date": "2025-05-01",
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_RANGE"


@pytest.mark.asyncio
async def test_meals_range_too_long_returns_400(client: httpx.AsyncClient):
    async with client as c:
        response = await c.get(
            "/api/meals",
            params={
                "edu_office_code": "B10",
                "school_code": "7010569",
                "from_date": "2025-01-01",
                "to_date": "2025-03-01",
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "RANGE_TOO_LONG"


@pytest.mark.asyncio
@respx.mock
async def test_meals_success_splits_br_separated_fields(client: httpx.AsyncClient):
    respx.get("https://open.neis.go.kr/hub/mealServiceDietInfo").mock(
        return_value=httpx.Response(
            200,
            json={
                "mealServiceDietInfo": [
                    {"head": [{"list_total_count": 1}, {"RESULT": {"CODE": "INFO-000", "MESSAGE": "정상"}}]},
                    {
                        "row": [
                            {
                                "MLSV_YMD": "20250519",
                                "DDISH_NM": "현미밥<br/>닭곰탕<br/>배추김치",
                                "ORPLC_INFO": "쌀(국내산)<br/>닭고기(국내산)",
                                "NTR_INFO": "탄수화물(g) : 120<br/>단백질(g) : 25",
                                "CAL_INFO": "682 Kcal",
                                "MLSV_FGR": "1200",
                            }
                        ]
                    },
                ]
            },
        )
    )

    async with client as c:
        response = await c.get(
            "/api/meals",
            params={
                "edu_office_code": "B10",
                "school_code": "7010569",
                "from_date": "2025-05-19",
                "to_date": "2025-05-19",
            },
        )

    assert response.status_code == 200
    meal = response.json()["meals"][0]
    assert meal["menu_items"] == ["현미밥", "닭곰탕", "배추김치"]
    assert meal["origin_items"] == ["쌀(국내산)", "닭고기(국내산)"]
    assert meal["calorie_info"] == "682 Kcal"
