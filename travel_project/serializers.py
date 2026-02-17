from concurrent.futures import ThreadPoolExecutor, as_completed

from rest_framework import serializers

from services.artwork import validate_artwork_exists
from travel_project.models import ProjectPlace, TravelProject


def _validate_artworks_exists(external_ids: list) -> dict:
    # TODO: a better way to do it?
    errors = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(validate_artwork_exists, eid): eid for eid in external_ids}
        for future in as_completed(futures):
            eid = futures[future]
            try:
                future.result()
            except ValueError as e:
                errors[eid] = str(e)
    return errors


class ProjectPlaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectPlace
        fields = ["id", "external_id", "notes", "visited"]
        read_only_fields = ["id"]


class TravelProjectSerializer(serializers.ModelSerializer):
    places = ProjectPlaceSerializer(many=True, required=False)

    class Meta:
        model = TravelProject
        fields = ["id", "name", "description", "start_date", "status", "places"]
        read_only_fields = ["id", "status"]

    def validate_places(self, value):
        if len(value) > 10:
            raise serializers.ValidationError("A project cannot have more than 10 places")

        external_ids = [place["external_id"] for place in value]
        if len(external_ids) != len(set(external_ids)):
            raise serializers.ValidationError("Duplicate places in request")

        if errors := _validate_artworks_exists(external_ids):
            raise serializers.ValidationError(errors)

        return value

    def create(self, validated_data):
        places_data = validated_data.pop("places", [])

        project = TravelProject.objects.create(**validated_data)

        ProjectPlace.objects.bulk_create([ProjectPlace(project=project, **place_data) for place_data in places_data])

        return project
