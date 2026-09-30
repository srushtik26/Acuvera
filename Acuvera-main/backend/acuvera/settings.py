"""
Acuvera Django Settings — 12-Factor, MVP configuration.
External services: PostgreSQL only (+ optional Clerk JWT, GROQ).
"""
import os
from pathlib import Path
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

# ─── Security ────────────────────────────────────────────────────────────────
SECRET_KEY = config("DJANGO_SECRET_KEY", default="dev-insecure-key-change-me")
DEBUG = config("DJANGO_DEBUG", default=True, cast=bool)
ALLOWED_HOSTS = config("DJANGO_ALLOWED_HOSTS", default="*", cast=Csv())

# Development-only auth bypass — blocked in production via guard in middleware
BYPASS_AUTH = config("BYPASS_AUTH", default=False, cast=bool)
if not DEBUG and BYPASS_AUTH:
    raise RuntimeError("BYPASS_AUTH=true is not permitted when DJANGO_DEBUG=false")

# ─── Applications ────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",        # Required by DRF internals even with custom auth
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    # Acuvera apps
    "core.apps.CoreConfig",
    "triage.apps.TriageConfig",
    "allocation.apps.AllocationConfig",
    "escalation.apps.EscalationConfig",
    "analytics.apps.AnalyticsConfig",
    "llm_sidecar.apps.LlmSidecarConfig",
    "fhir_adapter.apps.FhirAdapterConfig",
    "scheduler.apps.SchedulerConfig",
]

# ─── Middleware ───────────────────────────────────────────────────────────────
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.common.CommonMiddleware",
    "core.middleware.RequestAuditMiddleware",
    "core.middleware.JWTAuthMiddleware",
    "core.middleware.FeatureFlagMiddleware",
]

ROOT_URLCONF = "acuvera.urls"
WSGI_APPLICATION = "acuvera.wsgi.application"

# ─── Database ────────────────────────────────────────────────────────────────
import dj_database_url  # noqa: E402 — conditional import

DATABASE_URL = config("DATABASE_URL", default=f"postgresql://postgres:abc123@localhost:5432/acuvera_db")
DATABASES = {
    "default": dj_database_url.parse(DATABASE_URL, conn_max_age=600, engine="django.db.backends.postgresql")
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ─── Templates (minimal — API-only, no HTML except admin) ────────────────────
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": ["django.template.context_processors.request"]},
    }
]

# ─── DRF ─────────────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],  # Custom JWT middleware handles auth
    "DEFAULT_PERMISSION_CLASSES": ["core.permissions.IsAuthenticatedViaJWT"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardPagination",
    "PAGE_SIZE": 50,
    "EXCEPTION_HANDLER": "core.exceptions.acuvera_exception_handler",
    # Prevent DRF from importing django.contrib.auth.models.AnonymousUser
    "UNAUTHENTICATED_USER": None,
    "UNAUTHENTICATED_TOKEN": None,
}

# ─── CORS ────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = config("CORS_ALLOWED_ORIGINS", default="http://localhost:5173,http://localhost:3000", cast=Csv())
CORS_ALLOW_CREDENTIALS = True

from corsheaders.defaults import default_headers
CORS_ALLOW_HEADERS = list(default_headers) + [
    "x-ambulance-key",
    "x-bypass-user-id",
]

# ─── Clerk JWT ───────────────────────────────────────────────────────────────
CLERK_SECRET_KEY = config("CLERK_SECRET_KEY", default="")
CLERK_PUBLISHABLE_KEY = config("CLERK_PUBLISHABLE_KEY", default="")

# ─── GROQ LLM ────────────────────────────────────────────────────────────────
GROQ_API_KEY = config("GROQ_API_KEY", default="")
LLM_ENABLED_DEFAULT = config("LLM_ENABLED_DEFAULT", default=False, cast=bool)
GROQ_MODEL = config("GROQ_MODEL", default="llama3-8b-8192")
GROQ_TIMEOUT_SECONDS = config("GROQ_TIMEOUT_SECONDS", default=10, cast=int)

# ─── FHIR ────────────────────────────────────────────────────────────────────
FHIR_BASIC_USERNAME = config("FHIR_BASIC_USERNAME", default="fhir_user")
FHIR_BASIC_PASSWORD = config("FHIR_BASIC_PASSWORD", default="fhir_password")

# ─── Operational ─────────────────────────────────────────────────────────────
MAX_DOCTOR_REJECTIONS = config("MAX_DOCTOR_REJECTIONS", default=3, cast=int)
MAX_CONCURRENT_ALLOCATION_RETRIES = config("MAX_CONCURRENT_ALLOCATION_RETRIES", default=3, cast=int)

# Default feature flags (overridden per-hospital in DB)
FEATURE_FLAGS_DEFAULT = {
    "LLM_ENABLED": LLM_ENABLED_DEFAULT,
    "VOICE_INPUT_ENABLED": config("VOICE_INPUT_ENABLED", default=False, cast=bool),
    "ANALYTICS_ADVANCED": config("ANALYTICS_ADVANCED", default=True, cast=bool),
    "FHIR_ENABLED": config("FHIR_ENABLED", default=True, cast=bool),
    "PWA_ENABLED": config("PWA_ENABLED", default=True, cast=bool),
}

# ─── Sentry ──────────────────────────────────────────────────────────────────
SENTRY_DSN = config("SENTRY_DSN", default="")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    def _scrub_phi(event, hint):
        """Strip PHI fields from Sentry error context."""
        PHI_KEYS = {"name", "contact_phone", "external_id", "dob", "raw_input_text"}
        for frame in event.get("exception", {}).get("values", []):
            for f in frame.get("stacktrace", {}).get("frames", []):
                for key in list(f.get("vars", {}).keys()):
                    if key in PHI_KEYS:
                        f["vars"][key] = "[PHI REDACTED]"
        return event

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False,
        before_send=_scrub_phi,
    )

# ─── Structured JSON Logging ─────────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        }
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "acuvera": {"handlers": ["console"], "level": "DEBUG" if DEBUG else "INFO", "propagate": False},
    },
}

# ─── Static & Timezone ───────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
USE_TZ = True
TIME_ZONE = "UTC"
LANGUAGE_CODE = "en-us"
