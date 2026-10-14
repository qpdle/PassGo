import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

def required_env(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise ImproperlyConfigured(f"Set {name} in your local .env file")
    return value

SECRET_KEY = required_env("DJANGO_SECRET_KEY")
DEBUG = os.environ.get("DJANGO_DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = [v.strip() for v in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if v.strip()]
CSRF_TRUSTED_ORIGINS = [v.strip() for v in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if v.strip()]
INSTALLED_APPS = ["django.contrib.contenttypes", "rest_framework"]
MIDDLEWARE = ["django.middleware.security.SecurityMiddleware", "django.middleware.common.CommonMiddleware", "django.middleware.csrf.CsrfViewMiddleware"]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
DATABASES = {"default": {"ENGINE": "django.db.backends.postgresql", "NAME": required_env("POSTGRES_DB"), "USER": required_env("POSTGRES_USER"), "PASSWORD": required_env("POSTGRES_PASSWORD"), "HOST": os.environ.get("POSTGRES_HOST", "db"), "PORT": os.environ.get("POSTGRES_PORT", "5432"), "CONN_MAX_AGE": 60, "OPTIONS": {"connect_timeout": 5}}}
LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
REST_FRAMEWORK = {"DEFAULT_AUTHENTICATION_CLASSES": [], "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"], "UNAUTHENTICATED_USER": None, "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"]}
# Auth and sessions are added with the custom user model in S1-09.
# At this stage the only API route is the public health endpoint.
