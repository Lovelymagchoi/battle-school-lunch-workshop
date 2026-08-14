"""애플리케이션 설정."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """환경 변수 기반 설정.

    민감한 값(NEIS_API_KEY)은 이 클래스를 통해서만 읽으며, API 응답에는 절대 노출하지 않는다.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    neis_api_key: str = ""
    neis_base_url: str = "https://open.neis.go.kr"
    cors_allow_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    request_timeout_seconds: float = 15.0
    database_path: str = "data/analysis.db"

    @property
    def cors_allow_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
