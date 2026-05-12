from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str
    manager_chat_id: int
    database_url: str = "sqlite:///./kapsula.db"
    enable_sheets: bool = False
    google_sheets_id: str = ""
    google_service_account_file: str = "service_account.json"
    follow_up_delay_hours: int = 24
    max_followups: int = 2
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
