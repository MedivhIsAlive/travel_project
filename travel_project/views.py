from django.db import transaction
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import filters, status
from rest_framework.mixins import CreateModelMixin, DestroyModelMixin, ListModelMixin, RetrieveModelMixin, UpdateModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from travel_project.filters import TravelProjectFilter
from travel_project.models import ProjectPlace, TravelProject
from travel_project.serializers import (
    AddPlaceSerializer,
    ProjectPlaceSerializer,
    ProjectPlaceUpdateSerializer,
    TravelProjectCreateSerializer,
    TravelProjectSerializer,
    TravelProjectUpdateSerializer,
)


@extend_schema_view(
    list=extend_schema(
        summary="List travel projects",
        responses=TravelProjectSerializer(many=True),
    ),
    retrieve=extend_schema(
        summary="Retrieve a travel project",
        responses=TravelProjectSerializer,
    ),
    create=extend_schema(
        summary="Create a travel project",
        request=TravelProjectCreateSerializer,
        responses={201: TravelProjectSerializer},
    ),
    partial_update=extend_schema(
        summary="Update a travel project",
        request=TravelProjectUpdateSerializer,
        responses=TravelProjectSerializer,
    ),
    update=extend_schema(
        summary="Update a travel project",
        request=TravelProjectUpdateSerializer,
        responses=TravelProjectSerializer,
    ),
    destroy=extend_schema(
        summary="Delete a travel project",
        responses={
            204: OpenApiResponse(description="Project deleted"),
            409: OpenApiResponse(description="Cannot delete project with visited places"),
        },
    ),
)
class TravelProjectViewSet(ModelViewSet):
    queryset = TravelProject.objects.prefetch_related("places")
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = TravelProjectFilter
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at", "start_date"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "create":
            return TravelProjectCreateSerializer
        elif self.action in ("update", "partial_update"):
            return TravelProjectUpdateSerializer
        else:
            return TravelProjectSerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.has_visited_places():
            return Response(
                {"detail": "Cannot delete project with visited places."},
                status=status.HTTP_409_CONFLICT,
            )
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    list=extend_schema(
        summary="List places in a project",
        responses=ProjectPlaceSerializer(many=True),
    ),
    retrieve=extend_schema(
        summary="Retrieve a place by external ID",
        responses=ProjectPlaceSerializer,
    ),
    create=extend_schema(
        summary="Add a place to a project",
        request=AddPlaceSerializer,
        responses={201: ProjectPlaceSerializer},
    ),
    partial_update=extend_schema(
        summary="Update a place",
        request=ProjectPlaceUpdateSerializer,
        responses=ProjectPlaceSerializer,
    ),
    destroy=extend_schema(
        summary="Remove a place from a project",
        responses={
            204: OpenApiResponse(description="Place removed"),
            409: OpenApiResponse(description="Cannot remove the last place from a project"),
        },
    ),
)
class ProjectPlaceViewSet(
    ListModelMixin, RetrieveModelMixin, CreateModelMixin, UpdateModelMixin, DestroyModelMixin, GenericViewSet
):
    pagination_class = None
    lookup_field = "external_id"

    def get_project(self):
        return get_object_or_404(TravelProject, pk=self.kwargs["project_pk"])

    def get_queryset(self):
        return ProjectPlace.objects.filter(project_id=self.kwargs["project_pk"])

    def get_serializer_class(self):
        match self.action:
            case "create":
                return AddPlaceSerializer
            case "partial_update":
                return ProjectPlaceUpdateSerializer
            case _:
                return ProjectPlaceSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.action == "create":
            context["project"] = self.get_project()
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        place = serializer.save()
        place.project.sync_status()
        return Response(ProjectPlaceSerializer(place).data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        place = self.get_object()
        project = place.project

        with transaction.atomic():
            TravelProject.objects.select_for_update().get(pk=project.pk)

            if project.places.count() <= 1:
                return Response(
                    {"detail": "Cannot remove the last place from a project."},
                    status=status.HTTP_409_CONFLICT,
                )

            place.delete()

        project.sync_status()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_update(self, serializer):
        serializer.save()
        serializer.instance.project.sync_status()
