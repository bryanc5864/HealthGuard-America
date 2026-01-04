"""
HealthGuard America - Configuration Settings
"""

from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "HealthGuard America"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/healthguard"
    DATABASE_POOL_SIZE: int = 10

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ML Models
    ML_MODELS_PATH: str = "./ml_models/weights"
    PROCEDURE_ENCODER_MODEL: str = "procedure_encoder"
    NOVA_CLASSIFIER_MODEL: str = "nova_classifier"
    ADDITIVE_SCORER_MODEL: str = "additive_scorer"

    # Model Inference
    PROCEDURE_MATCH_THRESHOLD: float = 0.80
    PROCEDURE_REVIEW_THRESHOLD: float = 0.65
    NOVA_CONFIDENCE_THRESHOLD: float = 0.60

    # External APIs
    OPENFOODFACTS_API_URL: str = "https://world.openfoodfacts.org/api/v2"
    CMS_DATA_URL: str = "https://data.cms.gov"

    # MAHA Index Weights
    MAHA_WEIGHT_PRICE_TRANSPARENCY: float = 0.20
    MAHA_WEIGHT_DRUG_AFFORDABILITY: float = 0.25
    MAHA_WEIGHT_FOOD_SUPPLY: float = 0.30
    MAHA_WEIGHT_ACCESS_EQUITY: float = 0.25

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
