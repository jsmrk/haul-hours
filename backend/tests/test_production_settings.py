import json
import os
import subprocess
import sys

import pytest


def load_settings(overrides):
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith(("DJANGO_", "ORS_", "OVERPASS_", "HAUL_HOURS_"))
                   and key not in {"VERCEL", "FRONTEND_ORIGINS", "PROVIDER_MODE"}}
    environment.update({"HAUL_HOURS_PRODUCTION": "true", "DJANGO_DEBUG": "false",
                        "DJANGO_SECRET_KEY": "test-only-production-secret-with-sufficient-length-0123456789",
                        "DJANGO_ALLOWED_HOSTS": "api.example.test", "FRONTEND_ORIGINS": "https://app.example.test",
                        "ORS_API_KEY": "test-only-routing-key", "PROVIDER_MODE": "live"})
    environment.update(overrides)
    return subprocess.run([sys.executable, "-c", "import json; from config import settings as s; "
                           "print(json.dumps({'ssl': s.SECURE_SSL_REDIRECT, 'hsts': s.SECURE_HSTS_SECONDS, "
                           "'hosts': s.ALLOWED_HOSTS, 'origins': s.CORS_ALLOWED_ORIGINS, "
                           "'proxy': s.SECURE_PROXY_SSL_HEADER, 'fallbacks': s.OVERPASS_FALLBACK_URLS}))"],
                          env=environment, capture_output=True, text=True, timeout=10)


@pytest.mark.parametrize("overrides", [
    {"DJANGO_DEBUG": "true"}, {"DJANGO_SECRET_KEY": "short"}, {"PROVIDER_MODE": "fixtures"},
    {"ORS_API_KEY": ""}, {"DJANGO_ALLOWED_HOSTS": ""}, {"DJANGO_ALLOWED_HOSTS": "*"},
    {"FRONTEND_ORIGINS": ""}, {"FRONTEND_ORIGINS": "http://app.example.test"},
    {"OVERPASS_URL": "http://stop.example.test/api/interpreter"},
])
def test_production_rejects_incomplete_or_insecure_settings(overrides):
    result = load_settings(overrides)
    assert result.returncode != 0
    assert "ImproperlyConfigured" in result.stderr
    assert "test-only-routing-key" not in result.stderr


def test_valid_production_settings_use_https_and_strip_environment_lists():
    result = load_settings({"DJANGO_ALLOWED_HOSTS": " api.example.test, api2.example.test ",
                            "FRONTEND_ORIGINS": " https://app.example.test, https://preview.example.test ",
                            "OVERPASS_FALLBACK_URLS": "https://backup.example.test/api/interpreter",
                            "VERCEL": "1"})
    assert result.returncode == 0, result.stderr
    settings = json.loads(result.stdout)
    assert settings["ssl"] and settings["hsts"] > 0
    assert settings["hosts"] == ["api.example.test", "api2.example.test"]
    assert settings["origins"] == ["https://app.example.test", "https://preview.example.test"]
    assert settings["proxy"] == ["HTTP_X_FORWARDED_PROTO", "https"]
    assert settings["fallbacks"] == ["https://backup.example.test/api/interpreter"]
