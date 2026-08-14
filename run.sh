#!/usr/bin/env bash
# 급식배틀 앱(백엔드 + 프론트엔드)을 한 번에 실행하는 스크립트 (bash)
# 사용법: NEIS_API_KEY="발급받은키" ./run.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_DIR="$REPO_ROOT/src/api"
WEB_DIR="$REPO_ROOT/src/web"

if [ ! -d "$API_DIR" ]; then
  echo "백엔드 디렉터리를 찾을 수 없습니다: $API_DIR" >&2
  exit 1
fi
if [ ! -d "$WEB_DIR" ]; then
  echo "프론트엔드 디렉터리를 찾을 수 없습니다: $WEB_DIR" >&2
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "uv를 찾을 수 없습니다. https://docs.astral.sh/uv/ 에서 먼저 설치해 주세요." >&2
  exit 1
fi
if ! command -v npm >/dev/null 2>&1; then
  echo "npm을 찾을 수 없습니다. Node.js를 먼저 설치해 주세요. (https://nodejs.org)" >&2
  exit 1
fi

if [ -z "${NEIS_API_KEY:-}" ] && [ ! -f "$API_DIR/.env" ]; then
  echo "경고: $API_DIR/.env 파일이 없습니다. .env.example을 복사한 후 NEIS_API_KEY를 설정하세요." >&2
  echo "경고: NEIS_API_KEY 없이는 백엔드가 NEIS API를 호출할 수 없습니다." >&2
fi

echo "백엔드 의존성을 확인합니다..."
(cd "$API_DIR" && uv sync)

if [ ! -d "$WEB_DIR/node_modules" ]; then
  echo "프론트엔드 의존성을 설치합니다..."
  (cd "$WEB_DIR" && npm install)
fi

echo "백엔드 서버를 시작합니다 (http://localhost:8000)..."
(cd "$API_DIR" && uv run uvicorn app.main:app --reload --port 8000) &
API_PID=$!

cleanup() {
  echo "백엔드 서버를 종료합니다..."
  kill "$API_PID" 2>/dev/null || true
  wait "$API_PID" 2>/dev/null || true
}
trap cleanup EXIT

echo "프론트엔드 개발 서버를 시작합니다 (http://localhost:5173)..."
(cd "$WEB_DIR" && npm run dev)

