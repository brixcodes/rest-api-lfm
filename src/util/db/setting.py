from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from pathlib import Path
from dotenv import load_dotenv
import logging

# --- Configuration de base ---
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
ENV_FILE = BASE_DIR / ".env"
load_dotenv(ENV_FILE)

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("config")


class Settings(BaseSettings):
    # --- Base de données ---
    DATABASE_URL: str

    # --- JWT ---
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # --- SMTP / Email ---
    SMTP_SERVER: str
    SMTP_PORT: int
    GMAIL_EMAIL: str
    GMAIL_PASSWORD: str
    GMAIL_USERNAME: str

    # --- Fichiers ---
    UPLOAD_STORAGE_PATH: str

    # --- Cinetpay ---
    CINETPAY_BASE_URL: str | None = None
    CINETPAY_API_KEY: str | None = None
    CINETPAY_DON_OUVERT_SITE_ID: str | None = None
    CINETPAY_DON_OUVERT_SECRET_KEY: str | None = None
    CINETPAY_INSCRIPTION_SITE_ID: str | None = None
    CINETPAY_INSCRIPTION_SECRET_KEY: str | None = None
    CINETPAY_PARAINAGE_SITE_ID: str | None = None
    CINETPAY_PARAINAGE_SECRET_KEY: str | None = None

    # --- Config Pydantic ---
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Validations ---
    @field_validator("DATABASE_URL", mode="before")
    def check_database_url(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("DATABASE_URL doit être défini et non vide.")
        return v

    @field_validator("SECRET_KEY", mode="before")
    def check_secret_key(cls, v):
        if not v:
            raise ValueError("SECRET_KEY doit être défini.")
        if len(v) < 32:
            logger.warning("La SECRET_KEY est trop courte (< 32 caractères).")
        return v

    # --- Logging sécurisé ---
    def log_config(self):
        logger.info("✅ Configuration chargée avec succès.")
        for key, value in self.model_dump().items():
            if any(secret in key.upper() for secret in ("PASSWORD", "SECRET", "OTP_SALT", "GMAIL")):
                value = "*****"
            logger.info(f"{key}: {value}")


# --- Initialisation ---
settings = Settings()

if __name__ == "__main__":
    settings.log_config()