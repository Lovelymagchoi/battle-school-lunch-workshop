# 데이터베이스 연동하기

## 선택한 데이터베이스

SQLite 관계형 데이터베이스를 선택한다. 별도 서버 없이 로컬 개발 환경에서 바로 실행할 수 있고, 분석 요청·학교·전문 에이전트 결과 사이의 참조 무결성과 트랜잭션을 보장할 수 있기 때문이다. 운영 환경에서 여러 인스턴스가 동시에 쓰는 경우에는 동일한 스키마를 PostgreSQL로 이전할 수 있다.

## 데이터 모델

- `schools`: NEIS 학교 코드와 학교명
- `analysis_requests`: 분석 일자, 승자/동점, 총평, 비교 결과
- `analysis_schools`: 분석 요청과 학교의 역할(`school_a`, `school_b`)
- `agent_results`: 학교별 전문 에이전트 이름, 1~5점, 분석 내용, 근거

세 전문 평가 에이전트는 Concurrent 단계에서 독립적으로 결과를 만들고, 최종 품질 게이트가 검증한 결과를 `POST /api/analyses`로 저장한다. 학교·요청·에이전트 결과는 하나의 SQLite 트랜잭션으로 저장되므로 중간 오류가 발생하면 전체가 롤백된다.

## 로컬 실행 및 마이그레이션

`DATABASE_PATH` 환경 변수로 파일 위치를 지정하며 기본값은 `data/analysis.db`이다. 애플리케이션이 처음 실행될 때 `CREATE TABLE IF NOT EXISTS` 스키마가 적용된다.

```powershell
cd src/api
uv run uvicorn app.main:app --reload
```

분석 저장:

```text
POST /api/analyses
GET  /api/analyses/{analysis_id}
```

운영 데이터베이스를 변경할 때는 `src/api/app/database.py`의 `SCHEMA`를 PostgreSQL 마이그레이션으로 옮기고, 기존 데이터 백업 후 적용한다.
