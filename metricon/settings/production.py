"""
Production settings for Railway deployment.

Required environment variables (set in Railway dashboard):
  DJANGO_SECRET_KEY   — long random string
  DATABASE_URL        — set automatically by Railway PostgreSQL plugin
  DJANGO_ALLOWED_HOSTS — e.g. your-app.up.railway.app

Optional:
  PORT                — set automatically by Railway
"""
import os

import dj_database_url

from .base import *  # noqa: F401, F403

# ── Security ────────────────────────────────────────────────────────────────
SECRET_KEY = os.environ['DJANGO_SECRET_KEY']
DEBUG = False

ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '*').split(',')

CSRF_TRUSTED_ORIGINS = [
    f"https://{host}"
    for host in os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',')
    if host
]

# ── Database (Railway PostgreSQL via DATABASE_URL) ───────────────────────────
DATABASES = {
    'default': dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",  # noqa: F405
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# ── Static files (WhiteNoise) ────────────────────────────────────────────────
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ── Security headers ─────────────────────────────────────────────────────────
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# ── Logging ──────────────────────────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.environ.get('DJANGO_LOG_LEVEL', 'WARNING'),
            'propagate': False,
        },
    },
}
