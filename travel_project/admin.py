from django.contrib import admin

from travel_project.models import ProjectPlace, TravelProject


class ProjectPlaceInline(admin.TabularInline):
    model = ProjectPlace
    extra = 0


@admin.register(TravelProject)
class TravelProjectAdmin(admin.ModelAdmin):
    list_display = ["name", "status", "start_date", "created_at"]
    list_filter = ["status"]
    search_fields = ["name"]
    inlines = [ProjectPlaceInline]


@admin.register(ProjectPlace)
class ProjectPlaceAdmin(admin.ModelAdmin):
    list_display = ["external_id", "title", "project", "visited"]
    list_filter = ["visited"]

