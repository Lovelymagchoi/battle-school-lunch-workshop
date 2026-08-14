# 급식배틀 백엔드 API

FastAPI 기반 백엔드입니다. NEIS 공개 API(`data/openapi.json` 참고)를 호출해 학교 검색과 중식 조회 기능을 제공합니다.

## 환경 변수

`.env.example`을 `.env`로 복사한 후 `NEIS_API_KEY`를 설정하세요.

```bash
cp .env.example .env
```

| 변수 | 설명 |
| --- | --- |
| `NEIS_API_KEY` | NEIS 공개 API 인증키 (필수) |
| `CORS_ALLOW_ORIGINS` | 프론트엔드 오리진 목록 (콤마 구분) |

## 실행

```bash
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

## 테스트

```bash
uv run pytest
```

## API

| Method | Path | 설명 |
| --- | --- | --- |
| GET | `/api/health` | liveness 확인 |
| GET | `/api/schools?name=` | 학교 이름 일부 검색 |
| GET | `/api/meals?edu_office_code=&school_code=&from_date=&to_date=` | 중식 조회 (최대 31일, `to_date >= from_date` 검증) |
