from unittest.mock import patch

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from services.api.models import AICArtwork
from travel_project.models import ProjectPlace, TravelProject


def _mock_validate(external_id):
    return AICArtwork(
        id=int(external_id),
        title=f"Artwork {external_id}",
        artist_display=f"Artist {external_id}",
        date_display="2000",
        thumbnail=None,
        image_id=None,
    )


VALIDATE_PATH = "travel_project.serializers.validate_artwork_exists"
BATCH_PATH = "travel_project.serializers._validate_artworks_batch"


class TravelProjectTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.project = TravelProject.objects.create(name="Test Project")

    def test_create_project(self):
        response = self.client.post("/api/projects/", {"name": "New Project"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "New Project")
        self.assertEqual(response.data["status"], "active")

    @patch(BATCH_PATH)
    def test_create_project_with_places(self, mock_batch):
        mock_batch.return_value = (
            {"100": _mock_validate("100"), "200": _mock_validate("200")},
            {},
        )
        response = self.client.post(
            "/api/projects/",
            {
                "name": "With Places",
                "places": [{"external_id": "100"}, {"external_id": "200"}],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data["places"]), 2)
        self.assertEqual(response.data["places"][0]["title"], "Artwork 100")

    def test_list_projects(self):
        response = self.client.get("/api/projects/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_project(self):
        response = self.client.get(f"/api/projects/{self.project.pk}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Test Project")

    def test_update_project(self):
        response = self.client.patch(
            f"/api/projects/{self.project.pk}/",
            {"name": "Updated"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Updated")

    def test_delete_project(self):
        response = self.client.delete(f"/api/projects/{self.project.pk}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_project_with_visited_place_blocked(self):
        ProjectPlace.objects.create(project=self.project, external_id="1", visited=True)
        response = self.client.delete(f"/api/projects/{self.project.pk}/")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)


class ProjectPlaceTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.project = TravelProject.objects.create(name="Test Project")

    @patch(VALIDATE_PATH, side_effect=_mock_validate)
    def test_add_place(self, _):
        response = self.client.post(
            f"/api/projects/{self.project.pk}/places/",
            {"external_id": "999"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["external_id"], "999")
        self.assertEqual(response.data["title"], "Artwork 999")

    @patch(VALIDATE_PATH, side_effect=_mock_validate)
    def test_duplicate_place_rejected(self, _):
        ProjectPlace.objects.create(project=self.project, external_id="999")
        response = self.client.post(
            f"/api/projects/{self.project.pk}/places/",
            {"external_id": "999"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(VALIDATE_PATH, side_effect=_mock_validate)
    def test_max_10_places_enforced(self, _):
        for i in range(10):
            ProjectPlace.objects.create(project=self.project, external_id=str(i))
        response = self.client.post(
            f"/api/projects/{self.project.pk}/places/",
            {"external_id": "extra"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_places(self):
        ProjectPlace.objects.create(project=self.project, external_id="1")
        response = self.client.get(f"/api/projects/{self.project.pk}/places/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_retrieve_place_by_external_id(self):
        ProjectPlace.objects.create(project=self.project, external_id="42", title="Test")
        response = self.client.get(f"/api/projects/{self.project.pk}/places/42/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["external_id"], "42")

    def test_update_notes_and_visited(self):
        ProjectPlace.objects.create(project=self.project, external_id="42")
        response = self.client.patch(
            f"/api/projects/{self.project.pk}/places/42/",
            {"notes": "Great place", "visited": True},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["notes"], "Great place")
        self.assertTrue(response.data["visited"])


class StatusSyncTests(TestCase):
    def setUp(self):
        self.project = TravelProject.objects.create(name="Sync Test")
        self.place = ProjectPlace.objects.create(project=self.project, external_id="1")

    def test_all_visited_completes_project(self):
        self.place.visited = True
        self.place.save()
        self.project.sync_status()
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, "completed")

    def test_unvisit_reactivates_project(self):
        self.place.visited = True
        self.place.save()
        self.project.sync_status()

        self.place.visited = False
        self.place.save()
        self.project.sync_status()
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, "active")
