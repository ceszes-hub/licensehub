# ruff: noqa: F403, F405
from .base import *  # noqa: F403, F405

DEBUG = True
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_ROOT = BASE_DIR / "media"
BACKUP_PATH = BASE_DIR / "backups"

TLS_MONITOR_CERT_PATH = BASE_DIR / "tests" / "missing-cert.pem"
