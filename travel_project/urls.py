from django.urls import include, path
from rest_framework.routers import DefaultRouter

from travel_project.views import ProjectPlaceViewSet, TravelProjectViewSet

router = DefaultRouter()
router.register(r"projects", TravelProjectViewSet, basename="project")

urlpatterns = [
    path(
        "projects/<int:project_pk>/places/",
        ProjectPlaceViewSet.as_view({"get": "list", "post": "create"}),
        name="project-place-list",
    ),
    path(
        "projects/<int:project_pk>/places/<str:external_id>/",
        ProjectPlaceViewSet.as_view({"get": "retrieve", "patch": "partial_update"}),
        name="project-place-detail",
    ),
    path("", include(router.urls)),
]
