"""
Django settings for StudyPilot AI (Module 1).

Configuration values come from environment variables (see .env.example).
"""
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load backend/.env if it exists (it is ignored by git).
load_dotenv(BASE_DIR / ".env")


def env_list(name: str, default: str = "") -> list[str]:
    """Read a comma-separated environment variable into a list."""
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY is not set. Copy backend/.env.example to backend/.env first."
    )

DEBUG = os.environ.get("DJANGO_DEBUG", "False").lower() == "true"

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "corsheaders",
    "rest_framework",
    "api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # CorsMiddleware should be placed as high as possible, before CommonMiddleware.
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# A simple local SQLite file for now. PostgreSQL will be set up in a later module.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# --- Django REST Framework ---
REST_FRAMEWORK = {
    # No authentication in Module 1.
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
}

# --- CORS: which frontend origins may call this API from the browser ---
CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
)



# --- StudyPilot AI Configuration ---

# OpenAI API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Model used by the real AI Agent
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

# Maximum time for an AI request
OPENAI_TIMEOUT_SECONDS = int(
    os.getenv("OPENAI_TIMEOUT_SECONDS", "30")
)

# Use free local mock responses instead of OpenAI
MOCK_AI = os.getenv("MOCK_AI", "false").lower() == "true"
