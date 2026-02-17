from dataclasses import dataclass
from typing import Any


@dataclass
class AICArtwork:
    id: int
    title: str
    artist_display: str
    date_display: str
    thumbnail: dict[str, Any] | None
    image_id: str | None

