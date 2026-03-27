from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "AutoAudit AI"
    app_version: str = "1.0.0"
    debug: bool = False

    # Groq API
    groq_api_key: str = ""
    groq_model: str = "llama3-70b-8192"
    groq_max_tokens: int = 2048
    groq_temperature: float = 0.1

    # Compliance thresholds
    gst_rate_electronics: float = 18.0      # Required GST% for electronics
    invoice_amount_limit: float = 300000.0  # Max allowed invoice amount (INR)

    # Risk scoring — investigations with score < this threshold are auto-fixed
    auto_fix_risk_threshold: float = 5.0

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()
