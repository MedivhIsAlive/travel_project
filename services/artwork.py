# services/artwork.py
from django.core.cache import cache

from services.api.models import AICArtwork

from .api.aic import aic_client
from .api.base_client import APIError, NotFoundError

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
        raise ValueError("Artwork not found in AIC API")
    except APIError:
        raise ValueError("Could not validate artwork, try again later")
