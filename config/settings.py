"""Settings for VolKit, a baobab frame. Every value comes from the environment;
.env.example lists them. Names shared across baobab pieces are in CONTRACT.md section 10."""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

SITE_NAME = env("SITE_NAME", default="VolKit")
SECRET_KEY = env("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "linkedtrust_auth",
    "frame",
    "ghost",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "frame.security.ScriptPolicyMiddleware",
]

ROOT_URLCONF = "config.urls"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "config.context.volkit",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "frame.views.site",
            ],
        },
    },
]

DATABASES = {"default": env.db("DATABASE_URL")}

AUTH_PASSWORD_VALIDATORS = []
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Sessions: host-only, HttpOnly, Lax (CONTRACT.md section 5).
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SAMESITE = "Lax"
# Named per app, so pieces on one host (localhost ports in development) keep separate sessions.
SESSION_COOKIE_NAME = "volkit_session"
CSRF_COOKIE_NAME = "volkit_csrftoken"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# --- Sign-in (CONTRACT.md section 1) ---
OIDC_ISSUER = env("OIDC_ISSUER", default="https://live.linkedtrust.us").rstrip("/")
AUTH_PROVIDERS = env.list("AUTH_PROVIDERS", default=["linkedtrust"])
LINKEDTRUST_URL = OIDC_ISSUER
LINKEDTRUST_CLIENT_ID = env("OIDC_CLIENT_ID")
LINKEDTRUST_CLIENT_SECRET = env("OIDC_CLIENT_SECRET")
LINKEDTRUST_SCOPES = "openid email profile trust"
LOGIN_URL = "/auth/login/"

# --- Pieces that embed this frame's cards or read its API (CONTRACT.md section 5) ---
EMBED_ORIGINS = env.list("EMBED_ORIGINS", default=[])
CORS_ALLOWED_ORIGINS = EMBED_ORIGINS
CORS_ALLOW_CREDENTIALS = True
CORS_URLS_REGEX = r"^/api/"
from corsheaders.defaults import default_headers  # noqa: E402

CORS_ALLOW_HEADERS = [*default_headers, "x-baobab"]

# Roots ask this frame who belongs to which org (CONTRACT.md, Open decision C).
# Empty disables that endpoint.
S2S_TOKEN = env("S2S_TOKEN", default="")

# --- Live updates (CONTRACT.md section 3). Needs Postgres and an ASGI server. ---
LIVE = env.bool("LIVE", default=True) and DATABASES["default"]["ENGINE"].endswith("postgresql")

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["frame.security.EmbedSessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
}

# --- VolKit's own settings. Unset: that card is off. ---
# The Ghost site (raisethevoices.org). Content key: published posts. Admin key
# ("id:secret"): each person's own drafts, matched by their email.
VOLKIT_GHOST_URL = env("VOLKIT_GHOST_URL", default="").rstrip("/")
VOLKIT_GHOST_CONTENT_KEY = env("VOLKIT_GHOST_CONTENT_KEY", default="")
VOLKIT_GHOST_ADMIN_KEY = env("VOLKIT_GHOST_ADMIN_KEY", default="")
# The cases app. Its own sign-in; the card is a link until it signs in with LinkedTrust.
VOLKIT_CASES_URL = env("VOLKIT_CASES_URL", default="").rstrip("/")
