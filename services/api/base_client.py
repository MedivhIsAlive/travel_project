import logging
import httpx

logger = logging.getLogger("travel_planner.api")


class BaseAPIClient:
    timeout: float = 5.0
    base_url: str = ""

    def __init__(self):
        self.client = httpx.Client(timeout=self.timeout)

    def request(
        self,
        method,
        url,
        *args,
        raise_on_error_code: bool = True,
        log_parameters: bool = True,
        headers: dict | None = None,
        log: bool = True,
        **kwargs,
    ):
        headers = headers or {}
        if log:
            logging.info(
                f'Start request {method.__name__.upper()}: "{url}" {kwargs if log_parameters else dict()}',
            )

        try:
            response = method(url, *args, headers=headers, **kwargs)
            if raise_on_error_code:
                response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            raise APIError("Request timed out")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise NotFoundError()
            raise APIError(f"API returned {e.response.status_code}")
        except httpx.RequestError as e:
            raise APIError(f"Could not reach API: {e}")


class APIError(Exception):
    pass


class NotFoundError(APIError):
    pass
