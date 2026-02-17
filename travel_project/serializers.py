from concurrent.futures import ThreadPoolExecutor, as_completed

from django.db import transaction
from rest_framework import serializers

from services.artwork import ArtworkValidationError, validate_artwork_exists
from travel_project.models import ProjectPlace, TravelProject


def _validate_artworks_batch(external_ids: list[str]) -> tuple[dict[str, object], dict[str, str]]:
    results = {}
    errors = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(validate_artwork_exists, eid): eid for eid in external_ids}
        for future in as_completed(futures):
            eid = futures[future]
            try:
                results[eid] = future.result()
            except ArtworkValidationError as e:
                errors[eid] = str(e)
            except Exception as e:
                errors[eid] = f"Unexpected error: {e}"
    return results, errors


def _build_place(project: TravelProject, external_id: str, artwork, notes: str = "") -> ProjectPlace:
    return ProjectPlace(
        project=project,
        external_id=external_id,
        title=getattr(artwork, "title", ""),
        artist=getattr(artwork, "artist_display", ""),
        notes=notes,
    )


class ProjectPlaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectPlace
        fields = ["id", "external_id", "title", "artist", "notes", "visited", "created_at", "updated_at"]
        read_only_fields = ["id", "title", "artist", "created_at", "updated_at"]


class ProjectPlaceUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectPlace
        fields = ["id", "external_id", "title", "artist", "notes", "visited", "created_at", "updated_at"]
        read_only_fields = ["id", "external_id", "title", "artist", "created_at", "updated_at"]


class TravelProjectSerializer(serializers.ModelSerializer):
    places = ProjectPlaceSerializer(many=True, read_only=True)

    class Meta:
        model = TravelProject
        fields = ["id", "name", "description", "start_date", "status", "places", "created_at", "updated_at"]
        read_only_fields = ["id", "status", "created_at", "updated_at"]


class _RepresentAsDetailMixin:
    def to_representation(self, instance):
        return TravelProjectSerializer(instance).data


class TravelProjectCreateSerializer(_RepresentAsDetailMixin, serializers.ModelSerializer):
    places = serializers.ListField(
        child=serializers.DictField(),
        required=True,
        min_length=1,
        max_length=10,
    )

    class Meta:
        model = TravelProject
        fields = ["id", "name", "description", "start_date", "status", "places", "created_at", "updated_at"]
        read_only_fields = ["id", "status", "created_at", "updated_at"]

    def validate_places(self, value):
        for item in value:
            if "external_id" not in item:
                raise serializers.ValidationError("Each place must include 'external_id'.")

        external_ids = [p["external_id"] for p in value]
        if len(external_ids) != len(set(external_ids)):
            raise serializers.ValidationError("Duplicate external_id values in request.")

        artworks, errors = _validate_artworks_batch(external_ids)
        if errors:
            raise serializers.ValidationError(errors)

        for p in value:
            p["_artwork"] = artworks[p["external_id"]]

        return value

    def create(self, validated_data):
        places_data = validated_data.pop("places", [])
        project = TravelProject.objects.create(**validated_data)
        ProjectPlace.objects.bulk_create(
            [_build_place(project, p["external_id"], p.pop("_artwork"), p.get("notes", "")) for p in places_data]
        )
        return project


class TravelProjectUpdateSerializer(_RepresentAsDetailMixin, serializers.ModelSerializer):
    class Meta:
        model = TravelProject
        fields = ["id", "name", "description", "start_date", "status", "created_at", "updated_at"]
        read_only_fields = ["id", "status", "created_at", "updated_at"]


class AddPlaceSerializer(serializers.Serializer):
    external_id = serializers.CharField(max_length=100)
    notes = serializers.CharField(required=False, default="", allow_blank=True)

    def validate(self, attrs):
        project = self.context["project"]

        if project.places.count() >= 10:
            raise serializers.ValidationError({"external_id": "Project already has the maximum of 10 places."})

        if project.places.filter(external_id=attrs["external_id"]).exists():
            raise serializers.ValidationError(
                {"external_id": f"Place {attrs['external_id']} already exists in this project."}
            )

        try:
            attrs["artwork"] = validate_artwork_exists(attrs["external_id"])
        except ArtworkValidationError as e:
            raise serializers.ValidationError({"external_id": str(e)})

        return attrs

    def create(self, validated_data):
        artwork = validated_data.pop("artwork")
        project = self.context["project"]

        with transaction.atomic():
            TravelProject.objects.select_for_update().get(pk=project.pk)

            if project.places.count() >= 10:
                raise serializers.ValidationError(
                    {"external_id": "Project already has the maximum of 10 places."}
                )

            if project.places.filter(external_id=validated_data["external_id"]).exists():
                raise serializers.ValidationError(
                    {"external_id": f"Place {validated_data['external_id']} already exists in this project."}
                )

            place = _build_place(
                project,
                validated_data["external_id"],
                artwork,
                validated_data.get("notes", ""),
            )
            place.save()

        return place
