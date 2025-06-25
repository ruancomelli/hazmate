from collections.abc import Iterator
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict
from pydantic import HttpUrl as Url
from requests_oauthlib import OAuth2Session

from hazmate.builder.queries.base import BASE_URL, SiteId

SEARCH_URL = BASE_URL / "products" / "search"


class SearchPaging(BaseModel):
    limit: int
    offset: int
    total: int


class SearchAttributeValue(BaseModel):
    id: str
    name: str
    meta: dict[str, Any] | None = None


class SearchAttribute(BaseModel):
    id: str
    name: str
    value_id: str | None = None
    value_name: str
    values: list[SearchAttributeValue] | None = None


class SearchPicture(BaseModel):
    id: str
    url: Url


class SearchSettings(BaseModel):
    exclusive: bool
    listing_strategy: str


class SearchResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    attributes: list[SearchAttribute]
    catalog_product_id: str
    children_ids: list[str]
    date_created: datetime
    description: str
    domain_id: str
    id: str
    keywords: str
    main_features: list[Any]  # Can be empty or contain various structures
    name: str
    pdp_types: list[str]
    pictures: list[SearchPicture]
    priority: str
    quality_type: str
    settings: SearchSettings
    site_id: str
    status: str
    type: str
    variations: list[Any]  # Can contain various structures


class SearchResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    keywords: str
    paging: SearchPaging
    query_type: str
    results: list[SearchResult]
    used_attributes: list[Any]


def search_items(
    session: OAuth2Session,
    query: str,
    site_id: SiteId,
    category_id: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> SearchResponse:
    """Search for products in Meli API."""
    params: dict[str, Any] = {
        "q": query,
        "site_id": site_id.value,
    }

    if category_id is not None:
        params["category"] = category_id
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
        response = search_items(session, query, site_id, limit, offset)
        yield response
        offset += response.paging.limit
        if offset >= response.paging.total:
            break
