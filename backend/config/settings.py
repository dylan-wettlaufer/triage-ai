# config/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    PROJECT_NAME: str = "MedSightAI"
    API_VERSION: str = "1.0.0"
    DEBUG_MODE: bool = False

    # Database settings
    DATABASE_URL: str = "postgresql://user:password@host:port/dbname"

    # AWS S3 (or Firebase) settings
    S3_BUCKET_NAME: str = "medsightai-uploads"
    AWS_ACCESS_KEY_ID: str = None # Set via environment variable
    AWS_SECRET_ACCESS_KEY: str = None # Set via environment variable

    # Model paths or Hugging Face model IDs
    LAYOUTLMV3_MODEL_ID: str = "microsoft/layoutlmv3-base"
    VIT_SKIN_MODEL_ID: str = "google/vit-base-patch16-224" # Placeholder
    VIT_XRAY_MODEL_ID: str = "google/vit-base-patch16-224" # Placeholder

    # Other settings
    UPLOAD_FOLDER: str = "temp_uploads"
    MAX_FILE_SIZE_MB: int = 20

settings = Settings()