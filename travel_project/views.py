from rest_framework import viewsets
from travel_project.models import TravelProject

class TravelProjectViewSet(viewsets.ModelViewSet):
    queryset = TravelProject.objects.all()
    # serializer_class = TravelProjectSerializer

    def perform_destroy(self, instance) -> None:
        return super().perform_destroy(instance)
