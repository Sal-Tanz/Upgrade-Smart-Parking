"""Application configuration via pydantic-settings."""
from pydantic_settings import BaseSettings
from pydantic import field_validator
from pathlib import Path

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./parking.db"

    # JWT
    SECRET_KEY: str = "change-this-in-production-use-openssl-rand-hex-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # MQTT
    MQTT_BROKER: str = "localhost"
    MQTT_PORT: int = 1883
    MQTT_TOPIC_BUZZER: str = "parking/buzzer/alert"
    MQTT_TOPIC_SLOT: str = "parking/slot/status"
    MQTT_TOPIC_ENTRY: str = "parking/vehicle/entry"

    # Paths
    SLOT_CONFIG_PATH: str = "data/slot_config.json"
    CAPTURE_DIR: str = "data/captures"
    DATASET_DIR: str = "data/training_dataset/plates"

    # ML thresholds
    ALPR_CONF_THRESHOLD: float = 0.5
    OCR_CONF_THRESHOLD: float = 0.5

    # Timezone
    TIMEZONE: str = "Asia/Jakarta"  # WIB (UTC+7)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Warn if SECRET_KEY is still the insecure default."""
        default_key = "change-this-in-production-use-openssl-rand-hex-32"
        if v == default_key:
            import logging
            logging.getLogger("config").warning(
                "SECRET_KEY is using the insecure default value! "
                "Set SECRET_KEY in .env or environment for production. "
                "Generate one with: openssl rand -hex 32"
            )
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v

settings = Settings()
