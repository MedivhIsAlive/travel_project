from django.db import models


class TravelProject(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        DRAFT = "draft", "Draft"
        COMPLETED = "completed", "Completed"

    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    start_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return f"{self.name} ({self.status})"

    def sync_status(self):
        if self.places.exists() and not self.places.filter(visited=False).exists():  # pyright: ignore[reportAttributeAccessIssue]
            self.status = self.Status.COMPLETED
            self.save(update_fields=["status"])


class ProjectPlace(models.Model):
    project = models.ForeignKey(
        TravelProject,
        on_delete=models.CASCADE,
        related_name="places"
    )
    # feels really uncomfortable doing this without ForeignKey
    external_id = models.CharField(max_length=100)
    notes = models.TextField(blank=True, null=True)
    visited = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "external_id"]
            )
        ]
