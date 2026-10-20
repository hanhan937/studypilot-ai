
"""
Django settings for StudyPilot AI.

Supports:
- Django REST Framework
- PostgreSQL / SQLite
- Anonymous guest sessions
- CSRF protection
- React development frontend
- AI Agent / Demo Mode
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv


# ---------- Base Configuration ----------

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def env_list(name: str, default: str = "") -> list[str]:
    """Read a comma-separated environment variable."""
    return [
        item.strip()
        for item in os.environ.get(name, default).split(",")
        if item.strip()
    ]


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")

if not SECRET_KEY:
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY is not set. "
        "Copy backend/.env.example to backend/.env first."
    )


DEBUG = os.environ.get(
    "DJANGO_DEBUG", "False"
).lower() == "true"


ALLOWED_HOSTS = env_list(
    "DJANGO_ALLOWED_HOSTS",
    "localhost,127.0.0.1",
)


# ---------- Security ----------

SECURE_PROXY_SSL_HEADER = (
    "HTTP_X_FORWARDED_PROTO",
    "https",
)

SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

SESSION_COOKIE_HTTPONLY = True

SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

SECURE_SSL_REDIRECT = (
    os.getenv(
        "DJANGO_SECURE_SSL_REDIRECT",
        "false",
    ).lower()
    == "true"
)


# ---------- Installed Applications ----------

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "corsheaders",
    "rest_framework",
    "api",
]


# ---------- Middleware ----------

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


ROOT_URLCONF = "config.urls"

WSGI_APPLICATION = "config.wsgi.application"

ASGI_APPLICATION = "config.asgi.application"


# ---------- Database ----------

DB_ENGINE = os.getenv(
    "DB_ENGINE",
    "sqlite",
)

if DB_ENGINE == "postgresql":

    database_options = {}

    if os.getenv("DB_SSLMODE"):
        database_options["sslmode"] = os.getenv(
            "DB_SSLMODE"
        )

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv(
                "DB_NAME",
                "studypilot_db",
            ),
            "USER": os.getenv(
                "DB_USER",
                "studypilot",
            ),
            "PASSWORD": os.getenv(
                "DB_PASSWORD",
                "",
            ),
            "HOST": os.getenv(
                "DB_HOST",
                "127.0.0.1",
            ),
            "PORT": os.getenv(
                "DB_PORT",
                "5433",
            ),
            "CONN_MAX_AGE": 60,
            "OPTIONS": database_options,
        }
    }

else:

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


# ---------- Django Defaults ----------

DEFAULT_AUTO_FIELD = (
    "django.db.models.BigAutoField"
)

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# ---------- REST Framework ----------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny"
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer"
    ],
}


# ---------- CORS Configuration ----------

# Local frontend ports used by Vite.
# Include both localhost and 127.0.0.1.

LOCAL_FRONTEND_ORIGINS = [
    f"http://localhost:{port}"
    for port in range(5173, 5181)
] + [
    f"http://127.0.0.1:{port}"
    for port in range(5173, 5181)
]


# Add production frontend origins through .env
# when deploying.

CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS"
) + LOCAL_FRONTEND_ORIGINS

# Required for Django session cookies.
CORS_ALLOW_CREDENTIALS = True


# ---------- CSRF Configuration ----------

# Browser POST requests from React must pass
# Django's CSRF origin validation.

CSRF_TRUSTED_ORIGINS = env_list(
    "CSRF_TRUSTED_ORIGINS"
) + LOCAL_FRONTEND_ORIGINS


# ---------- AI Configuration ----------

OPENAI_API_KEY = os.getenv(
    "OPENAI_API_KEY",
    "",
)

OPENAI_MODEL = os.getenv(
    "OPENAI_MODEL",
    "gpt-4.1-mini",
)

OPENAI_TIMEOUT_SECONDS = int(
    os.getenv(
        "OPENAI_TIMEOUT_SECONDS",
        "30",
    )
)

MOCK_AI = (
    os.getenv(
        "MOCK_AI",
        "false",
    ).lower()
    == "true"
)
