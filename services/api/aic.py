from services.api.base_client import BaseAPIClient
from services.api.models import AICArtwork
from utility.collections import filtered_dict


class AICClient(BaseAPIClient):
    base_url = "https://api.artic.edu/api/v1"

    def get_artwork(self, external_id: str, **kwargs) -> AICArtwork:
        data = self.request(
            self.client.get,
            f"{self.base_url}/artworks/{external_id}",
            **kwargs,
        )
        raw = data["data"]
        return AICArtwork(
            id=raw["id"],
            title=raw.get("title", ""),
            artist_display=raw.get("artist_display", ""),
            date_display=raw.get("date_display", ""),
            thumbnail=raw.get("thumbnail"),
            image_id=raw.get("image_id"),
        )

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
        return data["data"]

    def search_artworks(self, query: str, *, page: int = 1, limit: int = 10) -> list[AICArtwork]:
        limit = max(1, min(limit, 100))
        data = self.request(
            self.client.get,
            f"{self.base_url}/artworks/search",
            params=filtered_dict(
                {
                    "q": query,
                    "page": page,
                    "limit": limit,
                    "fields": "id,title,artist_display,date_display,thumbnail,image_id",
                }
            ),
        )
        return [
            AICArtwork(
                id=item["id"],
                title=item.get("title", ""),
                artist_display=item.get("artist_display", ""),
                date_display=item.get("date_display", ""),
                thumbnail=item.get("thumbnail"),
                image_id=item.get("image_id"),
            )
            for item in data.get("data", [])
        ]


aic_client = AICClient()
