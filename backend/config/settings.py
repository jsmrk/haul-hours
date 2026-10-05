import math
import os
from pathlib import Path
from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
DEBUG = os.getenv("DJANGO_DEBUG", "false").lower() == "true"
PRODUCTION = bool(os.getenv("VERCEL")) or os.getenv("HAUL_HOURS_PRODUCTION", "false").lower() == "true"
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "local-development-only-change-before-hosting")
ALLOWED_HOSTS = [value.strip() for value in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",") if value.strip()]
INSTALLED_APPS = ["rest_framework", "corsheaders", "planner"]
MIDDLEWARE = ["django.middleware.security.SecurityMiddleware", "corsheaders.middleware.CorsMiddleware",
              "django.middleware.common.CommonMiddleware", "django.middleware.csrf.CsrfViewMiddleware",
              "django.middleware.clickjacking.XFrameOptionsMiddleware"]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
DATABASES = {}
USE_TZ = True
TIME_ZONE = "UTC"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
CORS_ALLOWED_ORIGINS = [value.strip() for value in os.getenv("FRONTEND_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173").split(",") if value.strip()]
REST_FRAMEWORK = {"UNAUTHENTICATED_USER": None, "DEFAULT_AUTHENTICATION_CLASSES": [],
                  "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
                  "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"]}
DATA_UPLOAD_MAX_MEMORY_SIZE = 4_000_000
ORS_API_KEY = os.getenv("ORS_API_KEY", "")
ORS_BASE_URL = os.getenv("ORS_BASE_URL", "https://api.heigit.org")
OVERPASS_URL = os.getenv("OVERPASS_URL", "https://overpass-api.de/api/interpreter")
# Backups are opt-in so a private endpoint never silently falls back to public infrastructure.
OVERPASS_FALLBACK_URLS = tuple(value.strip() for value in os.getenv("OVERPASS_FALLBACK_URLS", "").split(",") if value.strip())
STOP_PROVIDER = os.getenv("STOP_PROVIDER", "dot")
TRUCK_PARKING_URL = os.getenv("TRUCK_PARKING_URL", "https://services.arcgis.com/xOi1kZaI0eWDREZv/arcgis/rest/services/NTAD_Truck_Stop_Parking/FeatureServer/0")
if STOP_PROVIDER not in ("dot", "overpass"):
    raise ImproperlyConfigured("STOP_PROVIDER must be dot or overpass.")
PROVIDER_MODE = os.getenv("PROVIDER_MODE", "live")
ORS_MIN_INTERVAL_S = float(os.getenv("ORS_MIN_INTERVAL_S", "2"))
OVERPASS_MIN_INTERVAL_S = float(os.getenv("OVERPASS_MIN_INTERVAL_S", "2"))
if any(not math.isfinite(value) or not 0 <= value <= 60 for value in (ORS_MIN_INTERVAL_S, OVERPASS_MIN_INTERVAL_S)):
    raise ImproperlyConfigured("Provider intervals must be finite seconds between 0 and 60.")
if PRODUCTION and (DEBUG or PROVIDER_MODE != "live" or SECRET_KEY == "local-development-only-change-before-hosting" or len(SECRET_KEY) < 50):
    raise ImproperlyConfigured("Hosting requires DJANGO_DEBUG=false, PROVIDER_MODE=live, and a stable random DJANGO_SECRET_KEY of at least 50 characters.")
if PRODUCTION:
    if not ORS_API_KEY.strip():
        raise ImproperlyConfigured("Hosting requires ORS_API_KEY on the server.")
    if not os.getenv("DJANGO_ALLOWED_HOSTS") or not ALLOWED_HOSTS or any("*" in host or "://" in host for host in ALLOWED_HOSTS):
        raise ImproperlyConfigured("Hosting requires explicit DJANGO_ALLOWED_HOSTS without wildcards or URL schemes.")
    if not CORS_ALLOWED_ORIGINS or not os.getenv("FRONTEND_ORIGINS") or any(urlsplit(origin).scheme != "https" for origin in CORS_ALLOWED_ORIGINS):
        raise ImproperlyConfigured("Hosting requires explicit HTTPS FRONTEND_ORIGINS.")
    if any(urlsplit(url).scheme != "https" or not urlsplit(url).hostname for url in (ORS_BASE_URL, OVERPASS_URL, TRUCK_PARKING_URL, *OVERPASS_FALLBACK_URLS)):
        raise ImproperlyConfigured("Hosting requires HTTPS routing and stop-provider URLs.")
if len(OVERPASS_FALLBACK_URLS) > 2:
    raise ImproperlyConfigured("Configure at most two fallback stop-provider URLs.")
CORS_EXPOSE_HEADERS = ["Content-Disposition", "X-Request-ID", "X-Haul-Hours-Provider-Mode"]
PROVIDER_USER_AGENT = "HaulHours/1.0 (trip planning assessment; OpenStreetMap attribution)"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_SSL_REDIRECT = PRODUCTION
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https") if os.getenv("VERCEL") or os.getenv("DJANGO_TRUST_PROXY", "false").lower() == "true" else None
SECURE_HSTS_SECONDS = 31_536_000 if PRODUCTION else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SESSION_COOKIE_SECURE = PRODUCTION
CSRF_COOKIE_SECURE = PRODUCTION
X_FRAME_OPTIONS = "DENY"
