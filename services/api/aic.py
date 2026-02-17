from django.core.cache import cache
from services.api.base_client import BaseAPIClient, NotFoundError, APIError
from services.api.models import AICArtwork
from utility.collections import filtered_dict


class AICClient(BaseAPIClient):
    base_url = "https://api.artic.edu/api/v1"

    def get_artwork(self, external_id: int, **kwargs) -> AICArtwork:
        data = self.request(
            self.client.get, f"{self.base_url}/artworks/{external_id}", **kwargs,
        )

        return data["data"]

    def get_all_artwork(self, *, page: int = 1, limit: int | None = None, **kwargs) -> list[AICArtwork]:
        # this api caps the limit at 100
        if isinstance(limit, (int,)) and (limit > 100 or limit < 0):
            raise ValueError(f"{limit} is < 0 or > 100")
        data = self.request(
            self.client.get,
            f"{self.base_url}/artworks",
            params=filtered_dict({"page": page, "limit": limit}),
            **kwargs,
        )
        return data["results"]

    def search_artwork(self, **kwargs) -> list[AICArtwork]:
        return []



aic_client = AICClient()
