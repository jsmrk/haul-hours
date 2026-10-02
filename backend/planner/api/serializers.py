import re
from datetime import timezone
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from rest_framework import serializers

from planner.contracts import DutyStatus, EventKind, Location, LogMetadata, TripRequest
from planner.routing.ors import timezone_at

US_ZONES = {"America/New_York", "America/Detroit", "America/Kentucky/Louisville", "America/Kentucky/Monticello",
            "America/Chicago", "America/Denver", "America/Boise", "America/Phoenix", "America/Los_Angeles",
            "America/Anchorage", "America/Juneau", "America/Nome", "America/Sitka", "America/Yakutat",
            "America/Metlakatla", "America/Adak", "Pacific/Honolulu"}


def valid_zone(value):
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError):
        raise serializers.ValidationError("Choose a valid IANA timezone.") from None
    return value


class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if isinstance(data, dict):
            extra = data.keys() - self.fields.keys()
            if extra:
                raise serializers.ValidationError({key: ["Unknown field."] for key in sorted(extra)})
        return super().to_internal_value(data)


class DecimalStringField(serializers.DecimalField):
    def to_internal_value(self, data):
        if not isinstance(data, str) or not re.fullmatch(r"\d+(?:\.\d{1,2})?", data):
            raise serializers.ValidationError("Use a decimal string with at most two decimal places.")
        return super().to_internal_value(data)


class AwareDateTimeField(serializers.DateTimeField):
    def to_internal_value(self, data):
        if not isinstance(data, str) or not re.search(r"(?:Z|[+-]\d{2}:\d{2})$", data):
            raise serializers.ValidationError("Include an explicit UTC offset or Z in the departure time.")
        return super().to_internal_value(data)


class LocationSerializer(StrictSerializer):
    id = serializers.CharField(max_length=240)
    label = serializers.CharField(max_length=500)
    longitude = serializers.FloatField(min_value=-180, max_value=180)
    latitude = serializers.FloatField(min_value=-90, max_value=90)
    timezone = serializers.CharField(max_length=100, validators=[valid_zone])

    def validate(self, data):
        lon, lat = data["longitude"], data["latitude"]
        bounds = (-125 <= lon <= -66 and 24 <= lat <= 49.5) or (-180 <= lon <= -129 and 51 <= lat <= 72) or (-161 <= lon <= -154 and 18 <= lat <= 23)
        actual = timezone_at(lon, lat)
        us_zone = actual in US_ZONES or actual.startswith(("America/Indiana/", "America/North_Dakota/"))
        if not bounds or not us_zone:
            raise serializers.ValidationError("Choose a location in the supported United States region.")
        if data["timezone"] != actual:
            raise serializers.ValidationError("The location timezone does not match its coordinates. Select the address again.")
        return data


class LogMetadataSerializer(StrictSerializer):
    driver_name = serializers.CharField(max_length=100, required=False, allow_null=True, allow_blank=True)
    carrier_name = serializers.CharField(max_length=120, required=False, allow_null=True, allow_blank=True)
    carrier_address = serializers.CharField(max_length=240, required=False, allow_null=True, allow_blank=True)
    truck_number = serializers.CharField(max_length=80, required=False, allow_null=True, allow_blank=True)
    trailer_number = serializers.CharField(max_length=80, required=False, allow_null=True, allow_blank=True)
    shipment_reference = serializers.CharField(max_length=100, required=False, allow_null=True, allow_blank=True)
    starting_odometer_miles = DecimalStringField(max_digits=12, decimal_places=2, min_value=Decimal("0"),
                                                required=False, allow_null=True)


class TripRequestSerializer(StrictSerializer):
    current_location = LocationSerializer()
    pickup_location = LocationSerializer()
    dropoff_location = LocationSerializer()
    cycle_used_hours = DecimalStringField(max_digits=4, decimal_places=2, min_value=Decimal("0"), max_value=Decimal("70"))
    departure_at = AwareDateTimeField(default_timezone=timezone.utc)
    log_timezone = serializers.CharField(max_length=100, validators=[valid_zone])
    metadata = LogMetadataSerializer(required=False, default=dict)

    def to_domain(self) -> TripRequest:
        data = self.validated_data
        return TripRequest(*(Location(**data[field]) for field in ("current_location", "pickup_location", "dropoff_location")),
                           data["cycle_used_hours"], data["departure_at"], data["log_timezone"], LogMetadata(**data["metadata"]))


class DutyEventSerializer(StrictSerializer):
    id = serializers.CharField()
    kind = serializers.ChoiceField(choices=[kind.value for kind in EventKind])
    status = serializers.ChoiceField(choices=[status.value for status in DutyStatus])
    start_at = serializers.DateTimeField()
    end_at = serializers.DateTimeField()
    start_location = LocationSerializer()
    end_location = LocationSerializer()
    distance_m = serializers.IntegerField(min_value=0)
    driving_leg_id = serializers.CharField(allow_null=True)
    reasons = serializers.ListField(child=serializers.CharField())
    poi_id = serializers.CharField(allow_null=True)


class CoordinateField(serializers.ListField):
    def __init__(self, **kwargs):
        super().__init__(child=serializers.FloatField(), min_length=2, max_length=2, **kwargs)


class GraphPointField(CoordinateField):
    pass


class RoadStepSerializer(StrictSerializer):
    instruction = serializers.CharField()
    distance_m = serializers.IntegerField(min_value=0)
    duration_s = serializers.IntegerField(min_value=0)
    geometry = serializers.ListField(child=CoordinateField())


class RoadLegSerializer(StrictSerializer):
    id = serializers.CharField()
    origin = LocationSerializer()
    destination = LocationSerializer()
    steps = RoadStepSerializer(many=True)
    distance_m = serializers.IntegerField(min_value=0)
    duration_s = serializers.IntegerField(min_value=0)


class TripSummarySerializer(StrictSerializer):
    pickup_arrival_at = serializers.DateTimeField()
    dropoff_arrival_at = serializers.DateTimeField()
    completed_at = serializers.DateTimeField()
    distance_m = serializers.IntegerField(min_value=0)
    driving_s = serializers.IntegerField(min_value=0)
    elapsed_s = serializers.IntegerField(min_value=0)
    on_duty_s = serializers.IntegerField(min_value=0)
    off_duty_s = serializers.IntegerField(min_value=0)
    fuel_stop_count = serializers.IntegerField(min_value=0)
    short_break_count = serializers.IntegerField(min_value=0)
    daily_rest_count = serializers.IntegerField(min_value=0)
    cycle_restart_count = serializers.IntegerField(min_value=0)


class LogIntervalSerializer(StrictSerializer):
    event_id = serializers.CharField(allow_null=True)
    status = serializers.ChoiceField(choices=[status.value for status in DutyStatus])
    start_at = serializers.DateTimeField()
    end_at = serializers.DateTimeField()
    distance_m = serializers.IntegerField(min_value=0)
    assumed_outside_trip = serializers.BooleanField()


class LogRemarkSerializer(StrictSerializer):
    at = serializers.DateTimeField()
    location_label = serializers.CharField()
    note = serializers.CharField()
    event_id = serializers.CharField(allow_null=True)


class GraphTickSerializer(StrictSerializer):
    elapsed_s = serializers.IntegerField(min_value=0)
    label = serializers.CharField()
    utc_offset_s = serializers.IntegerField()


class GraphPathSerializer(StrictSerializer):
    event_id = serializers.CharField(allow_null=True)
    points = serializers.ListField(child=GraphPointField())


class LogGraphSerializer(StrictSerializer):
    ticks = GraphTickSerializer(many=True)
    paths = GraphPathSerializer(many=True)


class DailyLogSerializer(StrictSerializer):
    date = serializers.DateField()
    timezone = serializers.CharField()
    start_at = serializers.DateTimeField()
    end_at = serializers.DateTimeField()
    duration_s = serializers.IntegerField(min_value=1)
    intervals = LogIntervalSerializer(many=True)
    totals_s = serializers.DictField(child=serializers.IntegerField(min_value=0))
    distance_m = serializers.IntegerField(min_value=0)
    remarks = LogRemarkSerializer(many=True)
    graph = LogGraphSerializer()


class PlanResultSerializer(StrictSerializer):
    request = TripRequestSerializer()
    assumptions = serializers.ListField(child=serializers.CharField())
    summary = TripSummarySerializer()
    road_legs = RoadLegSerializer(many=True)
    events = DutyEventSerializer(many=True)
    daily_logs = DailyLogSerializer(many=True)
    warnings = serializers.ListField(child=serializers.CharField())
    planner_version = serializers.CharField()
    export_token = serializers.CharField()


class LocationSearchResultSerializer(StrictSerializer):
    locations = LocationSerializer(many=True)


class PlanningProblemSerializer(StrictSerializer):
    code = serializers.CharField()
    message = serializers.CharField()
    retryable = serializers.BooleanField()
    field_errors = serializers.DictField(child=serializers.ListField(child=serializers.CharField()))
    safe_prefix = DutyEventSerializer(many=True)


class PDFExportRequestSerializer(StrictSerializer):
    export_token = serializers.CharField(max_length=4_000_000)
    metadata = LogMetadataSerializer(required=False, default=dict)
    date = serializers.DateField(required=False)
