from collections.abc import AsyncIterator, Iterator
from datetime import datetime
from typing import Any

from asyncer import asyncify
from pydantic import ConfigDict
from pydantic import HttpUrl as Url

from hazmate.builder.queries.base import BASE_URL, ApiResponseModel, SiteId
from hazmate.builder.queries.product import Attribute, MainFeature
from hazmate.utils.oauth import OAuth2Session

SEARCH_URL = BASE_URL / "products" / "search"


class SearchPaging(ApiResponseModel):
    limit: int
    offset: int
    total: int


class SearchPicture(ApiResponseModel):
    id: str
    url: Url


class SearchSettings(ApiResponseModel):
    exclusive: bool
    listing_strategy: str


class SearchResult(ApiResponseModel):
    model_config = ConfigDict(frozen=True)

    attributes: tuple[Attribute, ...]
    catalog_product_id: str | None = None
    children_ids: tuple[str, ...]
    date_created: datetime
    description: str
    domain_id: str
    id: str
    keywords: str
    main_features: tuple[MainFeature, ...]  # Can be empty or contain various structures
    name: str
    pdp_types: tuple[str, ...]
    pictures: tuple[SearchPicture, ...]
    priority: str
    quality_type: str | None = None
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


async def search_products(
    session: OAuth2Session,
    site_id: SiteId,
    query: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> SearchResponse:
    """Search for products in Meli API."""
    # Example of https://api.mercadolibre.com/products/search
    #     {'keywords': 'dinossauro',
    #     'paging': {'limit': 2, 'offset': 0, 'total': 2},
    #     'query_type': 'PRODUCT_NAME',
    #     'results': [{'attributes': [{'id': 'BRAND',
    #                                 'name': 'Marca',
    #                                 'value_id': '45462093',
    #                                 'value_name': 'Ladai'},
    #                                 {'id': 'MANUFACTURER',
    #                                 'name': 'Fabricante',
    #                                 'value_id': '40609884',
    #                                 'value_name': 'DINO STATE'},
    #                                 {'id': 'COLLECTION',
    #                                 'name': 'Coleção',
    #                                 'value_id': '50140828',
    #                                 'value_name': 'dinossauro perigoso'},
    #                                 {'id': 'HEIGHT',
    #                                 'name': 'Altura',
    #                                 'value_id': '1006867',
    #                                 'value_name': '15 cm'},
    #                                 {'id': 'MATERIALS',
    #                                 'name': 'Materiais',
    #                                 'value_name': 'Plástico'},
    #                                 {'id': 'IS_COLLECTIBLE',
    #                                 'name': 'É colecionável',
    #                                 'value_id': '242085',
    #                                 'value_name': 'Sim'},
    #                                 {'id': 'INCLUDES_ACCESSORIES',
    #                                 'name': 'Inclui acessórios',
    #                                 'value_id': '242084',
    #                                 'value_name': 'Não'}],
    #                 'catalog_product_id': 'MLB47606852',
    #                 'children_ids': [],
    #                 'date_created': '2025-03-31T17:30:27Z',
    #                 'description': '',
    #                 'domain_id': 'MLB-ACTION_FIGURES',
    #                 'id': 'MLB47606852',
    #                 'keywords': 'Dinossauro Tyrannosaurus Rex - Dinossauro '
    #                             'Som/Perigoso',
    #                 'main_features': [],
    #                 'name': 'Dinossauro Tyrannosaurus Rex - Dinossauro Som/Perigoso',
    #                 'pdp_types': [],
    #                 'pictures': [{'id': '929518-MLA83444693269_032025',
    #                                 'url': 'https://http2.mlstatic.com/D_NQ_NP_929518-MLA83444693269_032025-F.jpg'},
    #                             {'id': '610995-MLA83153900696_032025',
    #                                 'url': 'https://http2.mlstatic.com/D_NQ_NP_610995-MLA83153900696_032025-F.jpg'}],
    #                 'priority': 'MEDIUM',
    #                 'quality_type': 'COMPLETE',
    #                 'settings': {'exclusive': False,
    #                             'listing_strategy': 'catalog_required'},
    #                 'site_id': 'MLB',
    #                 'status': 'active',
    #                 'type': 'PRODUCT',
    #                 'variations': []},
    #                 {'attributes': [{'id': 'BRAND',
    #                                 'name': 'Marca',
    #                                 'value_id': '40609884',
    #                                 'value_name': 'DINO STATE'},
    #                                 {'id': 'COLLECTION',
    #                                 'name': 'Coleção',
    #                                 'value_id': '50444225',
    #                                 'value_name': 'DINOSSAURO PERIGOSO'},
    #                                 {'id': 'IS_COLLECTIBLE',
    #                                 'name': 'É colecionável',
    #                                 'value_id': '242085',
    #                                 'value_name': 'Sim'},
    #                                 {'id': 'INCLUDES_ACCESSORIES',
    #                                 'name': 'Inclui acessórios',
    #                                 'value_id': '242084',
    #                                 'value_name': 'Não'},
    #                                 {'id': 'IS_BOBBLEHEAD',
    #                                 'name': 'É bobblehead',
    #                                 'value_id': '242084',
    #                                 'value_name': 'Não'},
    #                                 {'id': 'INCLUDES_CELL_BATTERIES',
    #                                 'name': 'Inclui pilhas',
    #                                 'value_id': '242084',
    #                                 'value_name': 'Não'},
    #                                 {'id': 'WITH_REMOTE_CONTROL',
    #                                 'name': 'Com controle remoto',
    #                                 'value_id': '242084',
    #                                 'value_name': 'Não'}],
    #                 'catalog_product_id': 'MLB47769460',
    #                 'children_ids': [],
    #                 'date_created': '2025-04-07T13:25:59Z',
    #                 'description': '',
    #                 'domain_id': 'MLB-ACTION_FIGURES',
    #                 'id': 'MLB47769460',
    #                 'keywords': 'Dinossauro Velociraptor - Som//Dinossauro perigoso '
    #                             'original',
    #                 'main_features': [],
    #                 'name': 'Dinossauro Velociraptor - Som//Dinossauro perigoso '
    #                         'original',
    #                 'pdp_types': [],
    #                 'pictures': [{'id': '893059-MLA83591410013_042025',
    #                                 'url': 'https://http2.mlstatic.com/D_NQ_NP_893059-MLA83591410013_042025-F.jpg'},
    #                             {'id': '928271-MLA83591537211_042025',
    #                                 'url': 'https://http2.mlstatic.com/D_NQ_NP_928271-MLA83591537211_042025-F.jpg'}],
    #                 'priority': 'MEDIUM',
    #                 'quality_type': 'COMPLETE',
    #                 'settings': {'exclusive': False,
    #                             'listing_strategy': 'catalog_required'},
    #                 'site_id': 'MLB',
    #                 'status': 'active',
    #                 'type': 'PRODUCT',
    #                 'variations': []}],
    #     'used_attributes': [{'id': 'COLLECTION',
    #                         'name': 'Coleção',
    #                         'value_id': '50140828',
    #                         'value_name': 'dinossauro perigoso'},
    #                         {'id': 'IS_COLLECTIBLE',
    #                         'name': 'É colecionável',
    #                         'value_id': '242085',
    #                         'value_name': 'Sim'},
    #                         {'id': 'INCLUDES_ACCESSORIES',
    #                         'name': 'Inclui acessórios',
    #                         'value_id': '242084',
    #                         'value_name': 'Não'}]}
    params: dict[str, Any] = {"site_id": site_id.value}
    if query is not None:
        params["q"] = query
    if limit is not None:
        params["limit"] = limit
    if offset is not None:
        params["offset"] = offset

    response = await session.get(SEARCH_URL, params=params)
    response.raise_for_status()

    return SearchResponse.model_validate(response.json())


async def search_products_paginated(
    session: OAuth2Session,
    site_id: SiteId,
    query: str | None = None,
    limit: int | None = None,
) -> AsyncIterator[SearchResponse]:
    """Search for products in Meli API, paginated.

    Args:
        session: The OAuth2 session to use.
        site_id: The site to search on.
        category_id: The category to search in.
        query: The query to search for.
        limit: The limit of products per page.
    """
    offset = 0
    while True:
        response = await search_products(
            session,
            site_id=site_id,
            query=query,
            limit=limit,
            offset=offset,
        )
        yield response
        offset += response.paging.limit
        if offset >= response.paging.total:
            break
