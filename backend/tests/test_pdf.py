from datetime import datetime, timedelta, timezone
from io import BytesIO

import pytest
from django.core.signing import TimestampSigner
from pypdf import PdfReader

from planner.contracts import LogMetadata
from planner.errors import PlanningProblem
from planner.logs.days import build_daily_logs
from planner.logs.pdf import draw_log_pdf
from planner.logs.tokens import sign_log_bundle, verify_log_bundle
from tests.test_logs import trip_at


def test_pdf_contains_same_day_totals_and_literal_metadata(trip_request):
    logs = build_daily_logs(trip_at(trip_request, datetime(2026, 10, 2, 12, tzinfo=timezone.utc), 7200))
    pdf = draw_log_pdf(logs, LogMetadata(driver_name="<Driver & Co>"))
    reader = PdfReader(BytesIO(pdf))
    text = " ".join(page.extract_text() for page in reader.pages)
    assert len(reader.pages) == 1
    assert "Projected driver daily log" in text and "2026-10-02" in text
    assert "02:00:00" in text and "22:00:00" in text
    assert "<Driver & Co>" in text and "Signature" in text
    assert "Assumed off duty outside planned trip" in text


def test_signed_bundle_round_trip_tampering_and_expiry(trip_request):
    now = datetime(2026, 10, 2, 12, tzinfo=timezone.utc)
    logs = build_daily_logs(trip_at(trip_request, now, 7200))
    token = sign_log_bundle(logs, now=now)
    assert verify_log_bundle(token, now) == logs
    with pytest.raises(PlanningProblem) as caught:
        verify_log_bundle(token[:-1] + ("A" if token[-1] != "A" else "B"), now)
    assert caught.value.status == 400
    with pytest.raises(PlanningProblem) as caught:
        verify_log_bundle(token, now + timedelta(seconds=86401))
    assert caught.value.status == 410


def test_signature_is_checked_before_decompression_and_decoded_size_is_bounded(trip_request, monkeypatch):
    import base64
    import zlib

    import planner.logs.tokens as tokens
    now = datetime.now(timezone.utc)
    with pytest.raises(PlanningProblem):
        verify_log_bundle("v1.9999999999.bad:unsigned", now)
    monkeypatch.setattr(tokens, "MAX_DECODED_BYTES", 1000)
    compressed = base64.urlsafe_b64encode(zlib.compress(b"a" * 1001)).decode()
    token = TimestampSigner(salt="haul-hours.logs.v1").sign("v1.9999999999." + compressed)
    with pytest.raises(PlanningProblem) as caught:
        verify_log_bundle(token, now)
    assert caught.value.status == 413
