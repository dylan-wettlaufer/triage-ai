# config/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    PROJECT_NAME: str = "TriageAI"
    API_VERSION: str = "1.0.0"
    DEBUG_MODE: bool = False

    DATABASE_URL: str = "postgresql://user:password@host:port/dbname"

    SUPABASE_URL: str
    SUPABASE_KEY: str # Use your anon public key or service role key for backend
    SUPABASE_STORAGE_BUCKET: str = "triageai-uploads" # Make sure this matches your bucket name in Supabase

    MAX_FILE_SIZE_MB: int = 20 # Maximum allowed file size for uploads

    # Add Hugging Face model IDs here later, e.g.:
    # LAYOUTLMV3_MODEL_ID: str = "microsoft/layoutlmv3-base"
    # VIT_SKIN_MODEL_ID: str = "google/vit-base-patch16-224"

settings = Settings()