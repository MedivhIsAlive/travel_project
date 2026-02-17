from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from django.test import TestCase, TransactionTestCase
from rest_framework import status
from rest_framework.test import APIClient

from services.api.models import AICArtwork
from travel_project.models import ProjectPlace, TravelProject


def _mock_validate(external_id):
    return AICArtwork(
        id=abs(hash(external_id)) % 10**6,
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
        self.client: APIClient = APIClient()

    @patch(BATCH_PATH)
    def test_create_project_populates_places_from_external_api(self, mock_batch):
        mock_batch.return_value = (
            {"100": _mock_validate("100"), "200": _mock_validate("200")},
            {},
        )
        response = self.client.post(
            "/api/projects/",
            {"name": "Trip", "places": [{"external_id": "100"}, {"external_id": "200"}]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "active")
        self.assertEqual(len(response.data["places"]), 2)
        self.assertEqual(response.data["places"][0]["title"], "Artwork 100")

    def test_delete_project_blocked_when_visited_places_exist(self):
        project = TravelProject.objects.create(name="P")
        ProjectPlace.objects.create(project=project, external_id="1", visited=True)
        response = self.client.delete(f"/api/projects/{project.pk}/")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_delete_project_allowed_when_no_visited_places(self):
        project = TravelProject.objects.create(name="P")
        ProjectPlace.objects.create(project=project, external_id="1", visited=False)
        response = self.client.delete(f"/api/projects/{project.pk}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(TravelProject.objects.filter(pk=project.pk).exists())


class ProjectPlaceTests(TestCase):
    def setUp(self):
        self.client: APIClient = APIClient()
        self.project = TravelProject.objects.create(name="P")
        ProjectPlace.objects.create(project=self.project, external_id="seed")

    @patch(VALIDATE_PATH, side_effect=_mock_validate)
    def test_add_place_populates_title_and_artist(self, _):
        response = self.client.post(
            f"/api/projects/{self.project.pk}/places/",
            {"external_id": "999"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], "Artwork 999")
        self.assertEqual(response.data["artist"], "Artist 999")

    def test_update_notes_and_visited(self):
        response = self.client.patch(
            f"/api/projects/{self.project.pk}/places/seed/",
            {"notes": "Great place", "visited": True},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["notes"], "Great place")
        self.assertTrue(response.data["visited"])

    def test_update_cannot_change_external_id(self):
        response = self.client.patch(
            f"/api/projects/{self.project.pk}/places/seed/",
            {"external_id": "hijacked"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["external_id"], "seed")


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


class PlaceCountBoundaryTests(TestCase):
    def setUp(self):
        self.client: APIClient = APIClient()

    def test_create_without_places_rejected(self):
        response = self.client.post("/api/projects/", {"name": "X"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_with_empty_places_rejected(self):
        response = self.client.post(
            "/api/projects/", {"name": "X", "places": []}, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_with_eleven_places_rejected(self):
        ids = [str(i) for i in range(11)]
        response = self.client.post(
            "/api/projects/",
            {"name": "Over", "places": [{"external_id": i} for i in ids]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(VALIDATE_PATH, side_effect=_mock_validate)
    def test_add_place_at_max_rejected(self, _):
        project = TravelProject.objects.create(name="Full")
        for i in range(10):
            ProjectPlace.objects.create(project=project, external_id=str(i))

        response = self.client.post(
            f"/api/projects/{project.pk}/places/",
            {"external_id": "extra"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(VALIDATE_PATH, side_effect=_mock_validate)
    def test_add_duplicate_rejected(self, _):
        project = TravelProject.objects.create(name="Dup")
        ProjectPlace.objects.create(project=project, external_id="42")

        response = self.client.post(
            f"/api/projects/{project.pk}/places/",
            {"external_id": "42"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_last_place_rejected(self):
        project = TravelProject.objects.create(name="Solo")
        ProjectPlace.objects.create(project=project, external_id="only")

        response = self.client.delete(f"/api/projects/{project.pk}/places/only/")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(project.places.count(), 1)

    def test_delete_one_of_two_accepted(self):
        project = TravelProject.objects.create(name="Pair")
        ProjectPlace.objects.create(project=project, external_id="a")
        ProjectPlace.objects.create(project=project, external_id="b")

        response = self.client.delete(f"/api/projects/{project.pk}/places/a/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(project.places.count(), 1)


class PlaceCountRaceConditionTests(TransactionTestCase):
    def setUp(self):
        self.client: APIClient = APIClient()
        self.project = TravelProject.objects.create(name="Race")

    @patch(VALIDATE_PATH, side_effect=_mock_validate)
    def test_concurrent_add_at_nine_cannot_exceed_ten(self, _):
        for i in range(9):
            ProjectPlace.objects.create(project=self.project, external_id=str(i))

        def add(eid):
            return self.client.post(
                f"/api/projects/{self.project.pk}/places/",
                {"external_id": eid},
                format="json",
            )

        with ThreadPoolExecutor(max_workers=2) as ex:
            results = [f.result() for f in [ex.submit(add, "a"), ex.submit(add, "b")]]

        codes = sorted(r.status_code for r in results)
        self.assertEqual(codes, [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST])
        self.assertLessEqual(self.project.places.count(), 10)

    def test_concurrent_delete_at_two_cannot_go_below_one(self):
        ProjectPlace.objects.create(project=self.project, external_id="x")
        ProjectPlace.objects.create(project=self.project, external_id="y")

        def delete(eid):
            return self.client.delete(f"/api/projects/{self.project.pk}/places/{eid}/")

        with ThreadPoolExecutor(max_workers=2) as ex:
            results = [f.result() for f in [ex.submit(delete, "x"), ex.submit(delete, "y")]]

        codes = sorted(r.status_code for r in results)
        self.assertIn(status.HTTP_204_NO_CONTENT, codes)
        self.assertIn(status.HTTP_409_CONFLICT, codes)
        self.assertGreaterEqual(self.project.places.count(), 1)
