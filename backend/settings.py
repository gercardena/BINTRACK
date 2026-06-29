"""
Django settings for bintrack project.
"""

import os
import sys
from datetime import timedelta
from pathlib import Path

from corsheaders.defaults import default_headers
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent

# Cargar archivo .env desde la raíz del proyecto.
load_dotenv(BASE_DIR / ".env")

# Permitir que Django encuentre las apps dentro de /apps.
sys.path.insert(0, os.path.join(BASE_DIR, "apps"))


def env_bool(name, default=False):
    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in [
        "1",
        "true",
        "yes",
        "on",
    ]


def env_list(name, default=""):
    value = os.getenv(name, default)

    return [
        item.strip()
        for item in value.split(",")
        if item.strip()
    ]


# ==============================
# Seguridad base
# ==============================

SECRET_KEY = (
    os.getenv("DJANGO_SECRET_KEY")
    or os.getenv("SECRET_KEY")
)

if not SECRET_KEY:
    raise ImproperlyConfigured(
        "SECRET_KEY no está configurada en .env"
    )

DEBUG = env_bool(
    "DJANGO_DEBUG",
    default=env_bool("DEBUG", default=False),
)

ALLOWED_HOSTS = env_list(
    "DJANGO_ALLOWED_HOSTS",
    default="127.0.0.1,localhost",
)

CORS_ALLOW_ALL_ORIGINS = env_bool(
    "DJANGO_CORS_ALLOW_ALL",
    default=DEBUG,
)

CORS_ALLOWED_ORIGINS = env_list(
    "DJANGO_CORS_ALLOWED_ORIGINS",
)

CORS_ALLOW_HEADERS = list(default_headers) + [
    "authorization",
]


# ==============================
# Apps
# ==============================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_extensions",

    # 3rd party
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",

    # apps locales
    "apps.accounts.apps.AccountsConfig",
    "apps.productos",
    "apps.inventario.apps.InventarioConfig",
    "apps.bins",
    "apps.ventas.apps.VentasConfig",
    "apps.payments.apps.PaymentsConfig",
    "apps.clientes",
    "apps.facturas",
    "apps.pagos",
]

AUTH_USER_MODEL = "accounts.User"


# ==============================
# Middleware
# ==============================

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


ROOT_URLCONF = "backend.urls"

TEMPLATES = [
    {
        "BACKEND": (
            "django.template.backends.django.DjangoTemplates"
        ),
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                (
                    "django.template.context_processors.request"
                ),
                (
                    "django.contrib.auth.context_processors.auth"
                ),
                (
                    "django.contrib.messages.context_processors.messages"
                ),
            ],
        },
    },
]

WSGI_APPLICATION = "backend.wsgi.application"


# ==============================
# Base de datos
# ==============================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": os.getenv("DB_HOST", "127.0.0.1"),
        "PORT": os.getenv("DB_PORT", "5432"),
    }
}


# ==============================
# Password validation
# ==============================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]


# ==============================
# Internacionalización
# ==============================

LANGUAGE_CODE = "es-cl"

TIME_ZONE = "America/Santiago"

USE_I18N = True

USE_TZ = True


# ==============================
# Static files
# ==============================

STATIC_URL = "static/"


# ==============================
# Django REST Framework
# ==============================

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication."
        "JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
}


# ==============================
# JWT
# ==============================

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "AUTH_HEADER_TYPES": ("Bearer",),
}


# ==============================
# Mercado Pago
# ==============================

MERCADOPAGO_ACCESS_TOKEN = os.getenv(
    "MERCADOPAGO_ACCESS_TOKEN",
)

MERCADOPAGO_PUBLIC_KEY = os.getenv(
    "MERCADOPAGO_PUBLIC_KEY",
)

MERCADOPAGO_ENV = os.getenv(
    "MERCADOPAGO_ENV",
    "sandbox",
)

MERCADOPAGO_NOTIFICATION_URL = os.getenv(
    "MERCADOPAGO_NOTIFICATION_URL",
)

MERCADOPAGO_SUCCESS_URL = os.getenv(
    "MERCADOPAGO_SUCCESS_URL",
)

MERCADOPAGO_FAILURE_URL = os.getenv(
    "MERCADOPAGO_FAILURE_URL",
)

MERCADOPAGO_PENDING_URL = os.getenv(
    "MERCADOPAGO_PENDING_URL",
)