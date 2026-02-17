from django.core.cache import cache

from services import APIError, NotFoundError
from services.api.aic import aic_client
from services.api.models import AICArtwork

CACHE_TTL = 60 * 60 * 6


class ArtworkValidationError(Exception):
    pass


def get_artwork(external_id: str) -> AICArtwork:
    cache_key = f"aic:artwork:{external_id}"

    if cached := cache.get(cache_key):
        return cached

    data = aic_client.get_artwork(external_id)
    cache.set(cache_key, data, CACHE_TTL)
    return data


def validate_artwork_exists(external_id: str) -> AICArtwork:
    try:
        return get_artwork(external_id)
    except NotFoundError:
        raise ArtworkValidationError(f"Artwork {external_id} not found in AIC API")
    except APIError:
        raise ArtworkValidationError(f"Could not validate artwork {external_id}, try again later")
