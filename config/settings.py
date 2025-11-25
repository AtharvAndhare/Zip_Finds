from pathlib import Path
from pydantic_settings import BaseSettings



# Path to.env file (located in project root)

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"



# Settings Model

class Settings(BaseSettings):
    # ---------- LLM Provider ----------
    LLM_PROVIDER: str = "openai"
    
    # --------- API Keys ---------
    OPENAI_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None
    AIRNOW_API_KEY: str | None = None
    HUD_API_KEY: str | None = None
    CENSUS_API_KEY: str | None = None

    # --------- Supabase ---------
    SUPABASE_URL: str | None = None
    SUPABASE_SERVICE_ROLE_KEY: str | None = None
    SUPABASE_ANON_KEY: str | None = None

    # --------- LLM Model ---------
    OPENAI_MODEL: str = "gpt-4.1-mini"

    # --------- MODE ---------
    USE_MOCK_DATA: bool = False

    # --------- SCORE WEIGHTS ---------
    SAFETY_WEIGHT: float = 0.22
    HEALTH_WEIGHT: float = 0.18
    EDUCATION_WEIGHT: float = 0.15
    HOUSING_WEIGHT: float = 0.13
    ECONOMIC_WEIGHT: float = 0.10
    DIGITAL_ACCESS_WEIGHT: float = 0.10
    ENVIRONMENT_WEIGHT: float = 0.07
    ACCESSIBILITY_WEIGHT: float = 0.05

    class Config:
        env_file = ENV_PATH
        extra = "allow"                      # Allows future keys safely


# Instantiate settings
settings = Settings()
