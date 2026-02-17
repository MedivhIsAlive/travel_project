from django.db import models


class TravelProject(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"

    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "travel_project"

    def __str__(self):
        return f"{self.name} ({self.status})"

    def sync_status(self):
        if self.places.exists() and not self.places.filter(visited=False).exists():  # pyright: ignore[reportAttributeAccessIssue]
            if self.status != self.Status.COMPLETED:
                self.status = self.Status.COMPLETED
                self.save(update_fields=["status"])
        elif self.status == self.Status.COMPLETED:
            self.status = self.Status.ACTIVE
            self.save(update_fields=["status", "updated_at"])

    def has_visited_places(self):
        return self.places.filter(visited=True).exists()  # pyright: ignore[reportAttributeAccessIssue]


class ProjectPlace(models.Model):
    project = models.ForeignKey(TravelProject, on_delete=models.CASCADE, related_name="places")
    external_id = models.CharField(max_length=100)
    title = models.CharField(max_length=500, blank=True, default="")
    artist = models.CharField(max_length=500, blank=True, default="")

    notes = models.TextField(blank=True, default="")
    visited = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "project_place"
        constraints = [models.UniqueConstraint(fields=["project", "external_id"], name="unique_place_per_project")]
