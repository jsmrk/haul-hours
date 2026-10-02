import math
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
DEBUG = os.getenv("DJANGO_DEBUG", "false").lower() == "true"
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "local-development-only-change-before-hosting")
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",")
INSTALLED_APPS = ["rest_framework", "corsheaders", "planner"]
MIDDLEWARE = ["django.middleware.security.SecurityMiddleware", "corsheaders.middleware.CorsMiddleware",
              "django.middleware.common.CommonMiddleware"]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
DATABASES = {}
USE_TZ = True
TIME_ZONE = "UTC"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
CORS_ALLOWED_ORIGINS = os.getenv("FRONTEND_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173").split(",")
REST_FRAMEWORK = {"UNAUTHENTICATED_USER": None, "DEFAULT_AUTHENTICATION_CLASSES": [],
                  "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
                  "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"]}
DATA_UPLOAD_MAX_MEMORY_SIZE = 4_000_000
ORS_API_KEY = os.getenv("ORS_API_KEY", "")
ORS_BASE_URL = os.getenv("ORS_BASE_URL", "https://api.openrouteservice.org")
OVERPASS_URL = os.getenv("OVERPASS_URL", "https://overpass-api.de/api/interpreter")
PROVIDER_MODE = os.getenv("PROVIDER_MODE", "live")
ORS_MIN_INTERVAL_S = float(os.getenv("ORS_MIN_INTERVAL_S", "2"))
OVERPASS_MIN_INTERVAL_S = float(os.getenv("OVERPASS_MIN_INTERVAL_S", "2"))
if any(not math.isfinite(value) or not 0 <= value <= 60 for value in (ORS_MIN_INTERVAL_S, OVERPASS_MIN_INTERVAL_S)):
    raise ImproperlyConfigured("Provider intervals must be finite seconds between 0 and 60.")
if os.getenv("VERCEL") and (DEBUG or PROVIDER_MODE != "live" or SECRET_KEY == "local-development-only-change-before-hosting" or len(SECRET_KEY) < 50):
    raise ImproperlyConfigured("Hosting requires DJANGO_DEBUG=false, PROVIDER_MODE=live, and a stable random DJANGO_SECRET_KEY of at least 50 characters.")
CORS_EXPOSE_HEADERS = ["Content-Disposition", "X-Request-ID", "X-Haul-Hours-Provider-Mode"]
PROVIDER_USER_AGENT = "HaulHours/1.0 (trip planning assessment; OpenStreetMap attribution)"
SECURE_CONTENT_TYPE_NOSNIFF = True
