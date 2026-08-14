"""API 요청/응답 모델.

`data/openapi.json`에 정의된 NEIS 응답 필드를 기준으로 하되,
프론트엔드에서 바로 사용할 수 있도록 필요한 필드만 추려 반환한다.
"""

from datetime import date

from typing import Any, Literal

from pydantic import BaseModel, Field


class SchoolSummary(BaseModel):
    """학교 검색 결과 항목."""

    school_code: str = Field(..., description="행정표준코드 (SD_SCHUL_CODE)")
    edu_office_code: str = Field(..., description="시도교육청코드 (ATPT_OFCDC_SC_CODE)")
    school_name: str = Field(..., description="학교명 (SCHUL_NM)")
    edu_office_name: str = Field(..., description="시도교육청명 (ATPT_OFCDC_SC_NM)")
    location_name: str = Field(..., description="시도명 (LCTN_SC_NM)")
    school_kind_name: str = Field(..., description="학교종류명 (SCHUL_KND_SC_NM)")


class SchoolSearchResponse(BaseModel):
    schools: list[SchoolSummary]


class MealInfo(BaseModel):
    """단일 날짜의 중식 정보."""

    meal_date: date = Field(..., description="급식일자")
    menu_items: list[str] = Field(default_factory=list, description="요리명 목록")
    origin_items: list[str] = Field(default_factory=list, description="원산지정보 목록")
    nutrition_items: list[str] = Field(default_factory=list, description="영양정보 목록")
    calorie_info: str | None = Field(default=None, description="칼로리정보")
    meal_headcount: str | None = Field(default=None, description="급식인원수")


class MealSearchResponse(BaseModel):
    school_code: str
    edu_office_code: str
    from_date: date
    to_date: date
    meals: list[MealInfo]


class ErrorBody(BaseModel):
    code: str
    message: str


class AgentResult(BaseModel):
    """병렬 전문 평가 에이전트 한 개의 구조화된 결과."""

    school_code: str
    agent_name: str = Field(..., min_length=1)
    score: int = Field(..., ge=1, le=5)
    analysis: str
    evidence: list[dict[str, Any]] = Field(default_factory=list)


class AnalysisCreate(BaseModel):
    """최종 품질 게이트를 통과한 비교 분석 저장 요청."""

    analysis_date: date
    school_a: SchoolSummary
    school_b: SchoolSummary
    agent_results: list[AgentResult] = Field(..., min_length=1)
    winner: Literal["school_a", "school_b", "tie"]
    overall_summary: str
    comparison_result: dict[str, Any] = Field(default_factory=dict)


class AnalysisResponse(AnalysisCreate):
    analysis_id: int
