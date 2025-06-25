from collections.abc import Iterator
from datetime import datetime
from typing import Any

from pydantic import ConfigDict
from pydantic import HttpUrl as Url

from hazmate.builder.queries.base import BASE_URL, ApiResponseModel, SiteId
from hazmate.utils.frozendict import FrozenDict
from hazmate.utils.oauth import OAuth2Session

SEARCH_URL = BASE_URL / "products" / "search"


class SearchPaging(ApiResponseModel):
    limit: int
    offset: int
    total: int


class SearchAttributeValue(ApiResponseModel):
    id: str
    name: str
    meta: FrozenDict[str, Any] | None = None


class SearchAttribute(ApiResponseModel):
    id: str
    name: str
    value_id: str | None = None
    value_name: str
    values: tuple[SearchAttributeValue, ...] | None = None


class SearchPicture(ApiResponseModel):
    id: str
    url: Url


class SearchSettings(ApiResponseModel):
    exclusive: bool
    listing_strategy: str


class SearchResult(ApiResponseModel):
    model_config = ConfigDict(frozen=True)

    attributes: tuple[SearchAttribute, ...]
    catalog_product_id: str
    children_ids: tuple[str, ...]
    date_created: datetime
    description: str
    domain_id: str
    id: str
    keywords: str
    main_features: tuple[Any, ...]  # Can be empty or contain various structures
    name: str
    pdp_types: tuple[str, ...]
    pictures: tuple[SearchPicture, ...]
    priority: str
    quality_type: str
    settings: SearchSettings
    site_id: str
    status: str
    type: str
    variations: tuple[Any, ...]  # Can contain various structures


class SearchResponse(ApiResponseModel):
    model_config = ConfigDict(frozen=True)

    keywords: str
    paging: SearchPaging
    query_type: str
    results: tuple[SearchResult, ...]
    used_attributes: tuple[Any, ...]


def search_products(
    session: OAuth2Session,
    query: str,
    site_id: SiteId,
    limit: int | None = None,
    offset: int | None = None,
) -> SearchResponse:
    """Search for products in Meli API."""
    params: dict[str, Any] = {
        "q": query,
        "site_id": site_id.value,
    }

    if limit is not None:
        params["limit"] = limit
    if offset is not None:
        params["offset"] = offset

    response = session.get(SEARCH_URL.human_repr(), params=params)
    response.raise_for_status()

    return SearchResponse.model_validate(response.json())


def search_products_paginated(
    session: OAuth2Session,
    query: str,
    site_id: SiteId,
    limit: int | None = None,
) -> Iterator[SearchResponse]:
    """Search for products in Meli API, paginated.

    Args:
        session: The OAuth2 session to use.
        query: The query to search for.
        site_id: The site to search on.
        limit: The limit of products to return.
    """
    offset = 0
    while True:
        response = search_products(session, query, site_id, limit, offset)
        yield response
        offset += response.paging.limit
        if offset >= response.paging.total:
            break
