from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "seo-agent-mvp"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@db:5432/seo_agent"

    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"
    LLM_PROVIDER: str = "gemini"

    WORDPRESS_BASE_URL: str = ""
    WORDPRESS_USERNAME: str = ""
    WORDPRESS_APP_PASSWORD: str = ""
    WORDPRESS_TIMEOUT: int = 30
    WORDPRESS_PER_PAGE: int = 100
    WORDPRESS_MAX_PAGES: int = 20
    WORDPRESS_CACHE_TTL_SECONDS: int = 300

    GENERATED_CONTENT_DIR: str = "generated_content"

    DEFAULT_LANGUAGE: str = "el"
    DEFAULT_COUNTRY: str = "GR"
    DEFAULT_CITY: str = "Athens"


settings = Settings()
