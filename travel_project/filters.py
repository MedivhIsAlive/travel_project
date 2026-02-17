from django_filters import rest_framework as filters

from travel_project.models import TravelProject


class TravelProjectFilter(filters.FilterSet):
    status = filters.ChoiceFilter(choices=TravelProject.Status.choices)
    start_date_from = filters.DateFilter(field_name="start_date", lookup_expr="gte")
    start_date_to = filters.DateFilter(field_name="start_date", lookup_expr="lte")
    name = filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = TravelProject
        fields = ["status", "name"]

