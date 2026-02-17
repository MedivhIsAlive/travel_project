from django.core.cache import cache

from services import APIError, NotFoundError
from services.api.aic import aic_client
from services.api.models import AICArtwork

CACHE_TTL = 60 * 60 * 6


def get_artwork(external_id: int) -> AICArtwork:
    cache_key = f"aic:artwork:{external_id}"

    if cached := cache.get(cache_key):
        return cached

    data = aic_client.get_artwork(external_id)
    cache.set(cache_key, data, CACHE_TTL)
    return data


def validate_artwork_exists(external_id: int) -> None:
    try:
        get_artwork(external_id)
    except NotFoundError:
        raise ValueError(f"Artwork {external_id} not found in AIC API")
    except APIError:
        raise ValueError(f"Could not validate artwork {external_id}, try again later")
