import enum
from collections.abc import Callable
from typing import Iterator, TypedDict

from yarl import URL

BASE_URL = URL("https://api.mercadolibre.com")


class SiteId(enum.StrEnum):
    ARGENTINA = "MLA"
    BRAZIL = "MLB"


class Paging(TypedDict):
    total: int
    offset: int
    limit: int


class PaginatedReponseJson[T](TypedDict):
    results: list[T]
    paging: Paging


def paginate[T](
    requester: Callable[[int], PaginatedReponseJson[T]],
) -> Iterator[T]:
    offset = 0
    while True:
        response = requester(offset)
        yield from response["results"]
        offset += response["paging"]["limit"]
        if offset >= response["paging"]["total"]:
            break
