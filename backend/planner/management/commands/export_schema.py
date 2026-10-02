import json
from pathlib import Path

from django.core.management.base import BaseCommand
from rest_framework import serializers

from planner.api import serializers as api


def export_contract_schema():
    definitions = {}

    def field_schema(field):
        if isinstance(field, serializers.ListSerializer):
            result = {"type": "array", "items": serializer_ref(field.child)}
        elif isinstance(field, serializers.Serializer):
            result = serializer_ref(field)
        elif isinstance(field, api.GraphPointField):
            result = {"type": "array", "items": [{"type": "number", "minimum": 0, "maximum": 1},
                                                 {"type": "integer", "minimum": 0, "maximum": 3}],
                      "minItems": 2, "maxItems": 2}
        elif isinstance(field, api.CoordinateField):
            result = {"type": "array", "items": [{"type": "number", "minimum": -180, "maximum": 180},
                                                 {"type": "number", "minimum": -90, "maximum": 90}],
                      "minItems": 2, "maxItems": 2}
        elif isinstance(field, serializers.ListField):
            result = {"type": "array", "items": field_schema(field.child)}
        elif isinstance(field, serializers.DictField):
            result = {"type": "object", "additionalProperties": field_schema(field.child)}
        elif isinstance(field, serializers.ChoiceField):
            result = {"type": "string", "enum": list(field.choices)}
        elif isinstance(field, serializers.BooleanField):
            result = {"type": "boolean"}
        elif isinstance(field, serializers.DecimalField):
            result = {"type": "string", "pattern": r"^\d+(?:\.\d{1,2})?$"}
        elif isinstance(field, serializers.IntegerField):
            result = {"type": "integer"}
        elif isinstance(field, serializers.FloatField):
            result = {"type": "number"}
        elif isinstance(field, serializers.DateTimeField):
            result = {"type": "string", "format": "date-time"}
        elif isinstance(field, serializers.DateField):
            result = {"type": "string", "format": "date"}
        elif isinstance(field, serializers.CharField):
            result = {"type": "string"}
        else:
            raise TypeError(f"Unsupported schema field: {type(field).__name__}")
        if result.get("type") == "string":
            if isinstance(field, serializers.CharField) and not field.allow_blank:
                result["minLength"] = 1
            if getattr(field, "max_length", None) is not None:
                result["maxLength"] = field.max_length
        if result.get("type") in ("number", "integer"):
            for attribute, keyword in (("min_value", "minimum"), ("max_value", "maximum")):
                value = getattr(field, attribute, None)
                if value is not None:
                    result[keyword] = value
        if field.allow_null:
            result = {"anyOf": [result, {"type": "null"}]}
        return result

    def serializer_ref(serializer):
        name = type(serializer).__name__.removesuffix("Serializer")
        if name not in definitions:
            definitions[name] = {}
            definitions[name] = {"type": "object", "additionalProperties": False,
                                 "properties": {key: field_schema(field) for key, field in serializer.fields.items()},
                                 "required": [key for key, field in serializer.fields.items() if field.required]}
        return {"$ref": f"#/definitions/{name}"}

    roots = [api.TripRequestSerializer(), api.PlanResultSerializer(), api.LocationSearchResultSerializer(),
             api.PlanningProblemSerializer(), api.PDFExportRequestSerializer()]
    return {"$schema": "http://json-schema.org/draft-07/schema#", "$id": "https://haul-hours.local/contracts/v1",
            "title": "HaulHoursContracts", "anyOf": [serializer_ref(root) for root in roots],
            "definitions": definitions}


class Command(BaseCommand):
    help = "Export JSON Schema directly from the API serializers."

    def add_arguments(self, parser):
        parser.add_argument("--output", required=True)

    def handle(self, *args, **options):
        output = Path(options["output"])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(export_contract_schema(), indent=2, sort_keys=True) + "\n")
        self.stdout.write(f"Exported {output}")
