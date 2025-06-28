from datetime import datetime
from typing import Any

from pydantic import ConfigDict
from pydantic import HttpUrl as Url

from hazmate.input_datasets.queries.base import BASE_URL, ApiResponseModel
from hazmate.utils.frozendict import FrozenDict
from hazmate.utils.oauth import OAuth2Session


class ChannelSettings(ApiResponseModel):
    channel: str
    settings: FrozenDict[str, Any]


class ChildCategory(ApiResponseModel):
    id: str
    name: str
    total_items_in_this_category: int


class PathFromRoot(ApiResponseModel):
    id: str
    name: str


class CategorySettings(ApiResponseModel):
    adult_content: bool
    buyer_protection_programs: tuple[str, ...]
    buying_allowed: bool
    buying_modes: tuple[str, ...]
    catalog_domain: str | None = None
    coverage_areas: str
    currencies: tuple[str, ...]
    fragile: bool
    immediate_payment: str
    item_conditions: tuple[str, ...]
    items_reviews_allowed: bool
    listing_allowed: bool
    max_description_length: int
    max_pictures_per_item: int
    max_pictures_per_item_var: int
    max_sub_title_length: int
    max_title_length: int
    max_variations_allowed: int
    maximum_price: float | None = None
    maximum_price_currency: str | None = None
    minimum_price: float | None = None
    minimum_price_currency: str | None = None
    mirror_category: str | None = None
    mirror_master_category: str | None = None
    mirror_slave_categories: tuple[str, ...]
    price: str
    reservation_allowed: str
    restrictions: tuple[str, ...]
    rounded_address: bool
    seller_contact: str
    shipping_options: tuple[str, ...]
    shipping_profile: str
    show_contact_information: bool
    simple_shipping: str
    status: str
    stock: str
    sub_vertical: str | None = None
    subscribable: bool
    tags: tuple[str, ...]
    vertical: str | None = None
    vip_subdomain: str


class CategoryDetail(ApiResponseModel):
    model_config = ConfigDict(frozen=True)

    attributable: bool
    attribute_types: str
    channels_settings: tuple[ChannelSettings, ...]
    children_categories: tuple[ChildCategory, ...]
    date_created: datetime
    id: str
    meta_categ_id: str | None = None
    name: str
    path_from_root: tuple[PathFromRoot, ...]
    permalink: Url
    picture: Url
    settings: CategorySettings
    total_items_in_this_category: int


async def get_category(session: OAuth2Session, category_id: str) -> CategoryDetail:
    """Get detailed information for a specific category from MercadoLibre API.

    Args:
        session: The OAuth2 session to use.
        category_id: The category ID to get details for.

    Returns:
        CategoryDetail model with detailed category information.

    Raises:
        requests.HTTPError: If the API request fails
        pydantic.ValidationError: If the response doesn't match the expected schema
    """
    # Example API response:
    # {'attributable': False,
    #  'attribute_types': 'variations',
    #  'channels_settings': [{'channel': 'mshops', 'settings': {'minimum_price': 0}},
    #                        {'channel': 'proximity',
    #                         'settings': {'status': 'disabled'}},
    #                        {'channel': 'mp-merchants',
    #                         'settings': {'buying_modes': ['buy_it_now'],
    #                                      'immediate_payment': 'required',
    #                                      'minimum_price': 0.01,
    #                                      'status': 'enabled'}},
    #                        {'channel': 'mp-link',
    #                         'settings': {'buying_modes': ['buy_it_now'],
    #                                      'immediate_payment': 'required',
    #                                      'minimum_price': 0.01,
    #                                      'status': 'enabled'}}],
    #  'children_categories': [{'id': 'MLB1747',
    #                           'name': 'Aces. de Carros e Caminhonetes',
    #                           'total_items_in_this_category': 10868630},
    #                          {'id': 'MLB1771',
    #                           'name': 'Aces. de Motos e Quadriciclos',
    #                           'total_items_in_this_category': 1982913},
    #                          {'id': 'MLB6005',
    #                           'name': 'Acessórios Náuticos',
    #                           'total_items_in_this_category': 124172},
    #                          {'id': 'MLB438364',
    #                           'name': 'Acessórios de Linha Pesada',
    #                           'total_items_in_this_category': 617844},
    #                          {'id': 'MLB2227',
    #                           'name': 'Ferramentas para Veículos',
    #                           'total_items_in_this_category': 462683},
    #                          {'id': 'MLB45468',
    #                           'name': 'GNV',
    #                           'total_items_in_this_category': 19910},
    #                          {'id': 'MLB457400',
    #                           'name': 'Instalações de pneus',
    #                           'total_items_in_this_category': 5},
    #                          {'id': 'MLB188063',
    #                           'name': 'Limpeza Automotiva',
    #                           'total_items_in_this_category': 503218},
    #                          {'id': 'MLB456111',
    #                           'name': 'Lubrificantes e Fluidos',
    #                           'total_items_in_this_category': 454428},
    #                          {'id': 'MLB458209',
    #                           'name': 'Motos',
    #                           'total_items_in_this_category': 0},
    #                          {'id': 'MLB8531',
    #                           'name': 'Navegadores GPS para Vehículos',
    #                           'total_items_in_this_category': 95169},
    #                          {'id': 'MLB5802',
    #                           'name': 'Outros',
    #                           'total_items_in_this_category': 153347},
    #                          {'id': 'MLB260634',
    #                           'name': 'Performance',
    #                           'total_items_in_this_category': 616434},
    #                          {'id': 'MLB456046',
    #                           'name': 'Peças Náuticas',
    #                           'total_items_in_this_category': 244897},
    #                          {'id': 'MLB22693',
    #                           'name': 'Peças de Carros e Caminhonetes',
    #                           'total_items_in_this_category': 71144713},
    #                          {'id': 'MLB419936',
    #                           'name': 'Peças de Linha Pesada',
    #                           'total_items_in_this_category': 3261103},
    #                          {'id': 'MLB243551',
    #                           'name': 'Peças de Motos e Quadriciclos',
    #                           'total_items_in_this_category': 6045926},
    #                          {'id': 'MLB2238',
    #                           'name': 'Pneus e Acessórios',
    #                           'total_items_in_this_category': 510962},
    #                          {'id': 'MLB255788',
    #                           'name': 'Rodas',
    #                           'total_items_in_this_category': 330960},
    #                          {'id': 'MLB2239',
    #                           'name': 'Segurança Veicular',
    #                           'total_items_in_this_category': 482626},
    #                          {'id': 'MLB377674',
    #                           'name': 'Serviços Programados',
    #                           'total_items_in_this_category': 880},
    #                          {'id': 'MLB3381',
    #                           'name': 'Som Automotivo',
    #                           'total_items_in_this_category': 1984655},
    #                          {'id': 'MLB455216',
    #                           'name': 'Tags de Pagamento de Pedágio',
    #                           'total_items_in_this_category': 33},
    #                          {'id': 'MLB1776',
    #                           'name': 'Tuning',
    #                           'total_items_in_this_category': 3018946}],
    #  'date_created': '2018-04-25T08:12:56.000Z',
    #  'id': 'MLB5672',
    #  'meta_categ_id': None,
    #  'name': 'Acessórios para Veículos',
    #  'path_from_root': [{'id': 'MLB5672', 'name': 'Acessórios para Veículos'}],
    #  'permalink': 'https://www.mercadolivre.com.br/c/acessorios-para-veiculos',
    #  'picture': 'https://http2.mlstatic.com/storage/categories-api/images/6fc20d84-2ce6-44ee-8e7e-e5479a78eab0.png',
    #  'settings': {'adult_content': False,
    #               'buyer_protection_programs': ['delivered', 'undelivered'],
    #               'buying_allowed': True,
    #               'buying_modes': ['auction', 'buy_it_now'],
    #               'catalog_domain': 'MLB-LIGHT_VEHICLE_ACCESSORIES',
    #               'coverage_areas': 'not_allowed',
    #               'currencies': ['BRL'],
    #               'fragile': False,
    #               'immediate_payment': 'required',
    #               'item_conditions': ['used', 'not_specified', 'new'],
    #               'items_reviews_allowed': False,
    #               'listing_allowed': False,
    #               'max_description_length': 50000,
    #               'max_pictures_per_item': 12,
    #               'max_pictures_per_item_var': 10,
    #               'max_sub_title_length': 70,
    #               'max_title_length': 60,
    #               'max_variations_allowed': 100,
    #               'maximum_price': None,
    #               'maximum_price_currency': 'BRL',
    #               'minimum_price': 0,
    #               'minimum_price_currency': 'BRL',
    #               'mirror_category': None,
    #               'mirror_master_category': None,
    #               'mirror_slave_categories': [],
    #               'price': 'required',
    #               'reservation_allowed': 'not_allowed',
    #               'restrictions': [],
    #               'rounded_address': False,
    #               'seller_contact': 'not_allowed',
    #               'shipping_options': ['custom'],
    #               'shipping_profile': 'optional',
    #               'show_contact_information': False,
    #               'simple_shipping': 'optional',
    #               'status': 'enabled',
    #               'stock': 'required',
    #               'sub_vertical': None,
    #               'subscribable': False,
    #               'tags': [],
    #               'vertical': None,
    #               'vip_subdomain': 'produto'},
    #  'total_items_in_this_category': 102926435}

    url = BASE_URL / "categories" / category_id

    response = await session.get(url)
    response.raise_for_status()

    return CategoryDetail.model_validate(response.json())
