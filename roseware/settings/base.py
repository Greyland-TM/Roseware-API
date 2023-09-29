"""
Django settings for Roseware API
"""

import os
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv

# Get the environment variables
# Import development or production settings based on the environment
if os.environ.get("DJANGO_ENV") == "development":
    from roseware.settings.development import *

    rabbitmq_username = os.environ.get("RABBITMQ_USER")
    rabbitmq_password = os.environ.get("RABBITMQ_PASSWORD")
    CELERY_BROKER_URL = (
        f"amqp://{rabbitmq_username}:{rabbitmq_password}@localhost:5672/"
    )
else:
    from roseware.settings.production import *

    CELERY_BROKER_URL = os.environ.get("CLOUDAMQP_URL")

load_dotenv()

# Set the project base directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(BASE_DIR, ".env")
SECRET_KEY = os.environ.get("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True
ALLOWED_HOSTS = ["*"]
CORS_ORIGIN_ALLOW_ALL = True
# CSRF_TRUSTED_ORIGINS = [os.environ.get("BACKEND_URL")]


# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_celery_results",
    "rest_framework",
    "knox",
    "corsheaders",
    "phonenumber_field",
    "apps.accounts",
    "apps.package_manager",
    "apps.pipedrive",
    "apps.stripe",
    "apps.monday",
    "apps.marketing_manager",
    "storages",
]

AUTHENTICATION_BACKENDS = [
    # 'apps.accounts.custom_auth_backend.CustomModelBackend',
    "django.contrib.auth.backends.ModelBackend",
    # ...
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
]

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ("knox.auth.TokenAuthentication",),
}

REST_AUTH_SERIALIZERS = {
    "USER_DETAILS_SERIALIZER": "project.apps.accounts.serializers.UserDetailsSerializer",
    "TOKEN_SERIALIZER": "project.apps.accounts.serializers.KnoxSerializer",
}

ROOT_URLCONF = "roseware.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "roseware.wsgi.application"

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# CELERY STUFF
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_RESULT_BACKEND = "django-db"
CELERY_CACHE_BACKEND = "django-cache"
CELERY_BROKER_USER = os.environ.get("RABBITMQ_USER")
CELERY_BROKER_PASSWORD = os.environ.get("RABBITMQ_PASSWORD")


# Password validation
# https://docs.djangoproject.com/en/4.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.0/howto/static-files/

STATIC_URL = "static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

# Default primary key field type
# https://docs.djangoproject.com/en/4.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_KNOX = {"TOKEN_TTL": timedelta(hours=24)}

# AWS Storage
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = os.environ.get("AWS_S3_BUCKET_NAME")
AWS_S3_REGION_NAME = "us-west-2"
DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
AWS_DEFAULT_ACL = None

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] [{module}] [{levelname}]: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "file": {
            "class": "logging.FileHandler",
            "filename": "logs/debug.log",
            "level": "DEBUG",
            "formatter": "verbose",
        },
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "": {
            "level": "INFO",
            "handlers": ["console"],
        },
        "django": {
            "handlers": ["file"],
            "level": "DEBUG",
            "propagate": False,
        },
        "django.server": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

if not os.path.exists("logs"):
    # Remove the 'file' handler from the LOGGING dictionary
    LOGGING["handlers"].pop("file", None)
    LOGGING["loggers"].pop("django", None)

else:
    # Only if logs directory exists, add the debug 'file' handler to LOGGING
    LOGGING["handlers"]["file"] = {
        "class": "logging.FileHandler",
        "filename": "logs/debug.log",
        "level": "DEBUG",
        "formatter": "verbose",
    }
