import base64
import json
import zlib
from datetime import datetime, timezone

from django.core.signing import BadSignature, TimestampSigner

from planner.constants import MAX_BODY_BYTES
from planner.contracts import DutyStatus, to_wire
from planner.errors import PlanningProblem
from planner.logs.contracts import DailyLog, GraphPath, GraphTick, LogGraph, LogInterval, LogRemark

MAX_DECODED_BYTES = MAX_BODY_BYTES


def sign_log_bundle(logs: tuple[DailyLog, ...], now: datetime | None = None) -> str:
    raw = json.dumps({"version": "1", "logs": to_wire(logs)}, separators=(",", ":"), ensure_ascii=True).encode()
    if len(raw) > MAX_DECODED_BYTES:
        raise PlanningProblem("RESULT_TOO_LARGE", "The daily logs exceed the export size limit.", 413)
    expires = int((now or datetime.now(timezone.utc)).timestamp()) + 86400
    encoded = base64.urlsafe_b64encode(zlib.compress(raw)).decode()
    return TimestampSigner(salt="haul-hours.logs.v1").sign(f"v1.{expires}.{encoded}")


def verify_log_bundle(token: str, now: datetime) -> tuple[DailyLog, ...]:
    if len(token) > MAX_BODY_BYTES:
        raise PlanningProblem("PAYLOAD_TOO_LARGE", "The export token exceeds the size limit.", 413)
    try:
        # Signature is verified before any base64 decoding, JSON parsing, or decompression.
        signed = TimestampSigner(salt="haul-hours.logs.v1").unsign(token)
        version, expires, encoded = signed.split(".", 2)
        if version != "v1":
            raise ValueError("Invalid version")
        if now.timestamp() > int(expires):
            raise PlanningProblem("EXPORT_EXPIRED", "This export has expired. Recalculate the trip to download its logs.", 410)
        compressed = base64.b64decode(encoded, altchars=b"-_", validate=True)
        decoder = zlib.decompressobj()
        raw = decoder.decompress(compressed, MAX_DECODED_BYTES + 1)
        if len(raw) > MAX_DECODED_BYTES or decoder.unconsumed_tail:
            raise PlanningProblem("PAYLOAD_TOO_LARGE", "The decoded export exceeds the size limit.", 413)
        if not decoder.eof or decoder.unused_data:
            raise ValueError("Invalid compression")
        bundle = json.loads(raw)
        if bundle["version"] != "1" or not 1 <= len(bundle["logs"]) <= 365:
            raise ValueError("Invalid log bundle")
        logs = []
        for data in bundle["logs"]:
            intervals = tuple(LogInterval(item["event_id"], DutyStatus(item["status"]),
                                          datetime.fromisoformat(item["start_at"]), datetime.fromisoformat(item["end_at"]),
                                          item["distance_m"], item["assumed_outside_trip"]) for item in data["intervals"])
            remarks = tuple(LogRemark(datetime.fromisoformat(item["at"]), item["location_label"], item["note"],
                                      item["event_id"]) for item in data["remarks"])
            graph = LogGraph(tuple(GraphTick(**tick) for tick in data["graph"]["ticks"]),
                             tuple(GraphPath(path["event_id"], tuple(tuple(point) for point in path["points"]))
                                   for path in data["graph"]["paths"]))
            logs.append(DailyLog(data["date"], data["timezone"], datetime.fromisoformat(data["start_at"]),
                                 datetime.fromisoformat(data["end_at"]), data["duration_s"], intervals,
                                 {DutyStatus(key): value for key, value in data["totals_s"].items()},
                                 data["distance_m"], remarks, graph))
        return tuple(logs)
    except (BadSignature, ValueError, TypeError, KeyError, zlib.error):
        raise PlanningProblem("INVALID_EXPORT_TOKEN", "The export token is invalid.", 400) from None
