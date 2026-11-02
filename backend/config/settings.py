import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
SECRET_KEY = (os.getenv("SECRET_KEY") or "local-demo-no-sessions-or-authentication")
ALLOWED_HOSTS = (os.getenv("ALLOWED_HOSTS") or "localhost,127.0.0.1,[::1],testserver").split(",")
INSTALLED_APPS = ["django.contrib.staticfiles", "planner"]
MIDDLEWARE = ["django.middleware.security.SecurityMiddleware", "django.middleware.gzip.GZipMiddleware", "whitenoise.middleware.WhiteNoiseMiddleware", "django.middleware.common.CommonMiddleware"]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
STATIC_URL = "/assets/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR.parent / "frontend/dist/assets"] if (BASE_DIR.parent / "frontend/dist/assets").exists() else []
STORAGES = {"staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"}}
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "OPTIONS": {"MAX_ENTRIES": 2500}}}
DATA_UPLOAD_MAX_MEMORY_SIZE = 1_000_000
USE_TZ = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
