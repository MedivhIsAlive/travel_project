from typing import TypedDict


class AICThumbnail(TypedDict):
    lqip: str
    width: int
    height: int


class AICArtwork(TypedDict):
    id: int
    title: str
    artist_display: str
    date_display: str
    thumbnail: AICThumbnail | None
    image_id: str | None
