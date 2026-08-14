"""분석 결과의 저장, 조회, 원자적 롤백을 검증한다."""

from datetime import date
import sqlite3

import httpx
import pytest
from httpx import ASGITransport

from app.database import AnalysisRepository
from app.main import app
from app.routes import get_analysis_repository
from app.schemas import AnalysisCreate, AgentResult, SchoolSummary


def school(code: str, name: str) -> SchoolSummary:
    return SchoolSummary(
        school_code=code,
        edu_office_code="B10",
        school_name=name,
        edu_office_name="서울특별시교육청",
        location_name="서울특별시",
        school_kind_name="고등학교",
    )


def analysis_request() -> AnalysisCreate:
    return AnalysisCreate(
        analysis_date=date(2025, 5, 19),
        school_a=school("1", "서울고등학교"),
        school_b=school("2", "부산고등학교"),
        agent_results=[
            AgentResult(
                school_code="1",
                agent_name="영양 균형 평가자",
                score=4,
                analysis="식품군이 다양합니다.",
                evidence=[{"field": "calorie_info", "value": "682 Kcal"}],
            ),
            AgentResult(
                school_code="2",
                agent_name="영양 균형 평가자",
                score=3,
                analysis="식품군 다양성이 보통입니다.",
            ),
        ],
        winner="school_a",
        overall_summary="서울고등학교가 우세합니다.",
        comparison_result={"nutrition": {"school_a": 4, "school_b": 3}},
    )


def test_repository_round_trip_preserves_analysis_data(tmp_path):
    repository = AnalysisRepository(str(tmp_path / "analysis.db"))

    analysis_id = repository.create(analysis_request())
    result = repository.get(analysis_id)

    assert result is not None
    assert result.analysis_date == date(2025, 5, 19)
    assert result.school_a.school_name == "서울고등학교"
    assert result.agent_results[0].score == 4
    assert result.winner == "school_a"
    assert result.comparison_result["nutrition"]["school_b"] == 3


def test_repository_rolls_back_when_agent_result_insert_fails(tmp_path):
    repository = AnalysisRepository(str(tmp_path / "analysis.db"))
    request = analysis_request()
    request.agent_results.append(request.agent_results[0])

    with pytest.raises(sqlite3.IntegrityError):
        repository.create(request)

    with repository._connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM analysis_requests").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM schools").fetchone()[0] == 0


@pytest.mark.asyncio
async def test_analysis_api_can_read_saved_result(tmp_path):
    database_path = str(tmp_path / "api.db")
    app.dependency_overrides[get_analysis_repository] = lambda: AnalysisRepository(database_path)
    try:
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            create_response = await client.post("/api/analyses", json=analysis_request().model_dump(mode="json"))
            analysis_id = create_response.json()["analysis_id"]
            read_response = await client.get(f"/api/analyses/{analysis_id}")

        assert create_response.status_code == 201
        assert read_response.status_code == 200
        assert read_response.json()["school_b"]["school_name"] == "부산고등학교"
    finally:
        app.dependency_overrides.clear()
