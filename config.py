"""Environment-based configuration. Secrets always come from environment variables."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("DATA_DIR", BASE_DIR / "instance"))


def _database_uri():
    url = os.environ.get("DATABASE_URL")
    if url:  # Render/Heroku sometimes give "postgres://", SQLAlchemy needs "postgresql://"
        return url.replace("postgres://", "postgresql://", 1)
    return f"sqlite:///{DATA_DIR / 'civicconnect.db'}"


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-insecure-key")
    SQLALCHEMY_DATABASE_URI = _database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DATA_DIR = DATA_DIR
    UPLOAD_FOLDER = str(DATA_DIR / "uploads")  # outside /static: never served publicly
    MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", 5))
    MAX_CONTENT_LENGTH = (MAX_UPLOAD_MB + 1) * 1024 * 1024
    ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}
    PER_PAGE = 10
    RATELIMIT_ENABLED = True
    MAIL_ENABLED = os.environ.get("MAIL_ENABLED", "false").lower() == "true"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    REMEMBER_COOKIE_HTTPONLY = True


class TestingConfig(Config):
    TESTING = True
    SECRET_KEY = "test-secret"
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite://"  # overridden by conftest with a temp file


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
