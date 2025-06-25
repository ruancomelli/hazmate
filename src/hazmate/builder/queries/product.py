from datetime import datetime
from typing import Any

from pydantic import ConfigDict
from pydantic import HttpUrl as Url

from hazmate.builder.queries.base import BASE_URL, ApiResponseModel
from hazmate.utils.frozendict import FrozenDict
from hazmate.utils.oauth import OAuth2Session

PRODUCT_URL = BASE_URL / "products"


class PickerProduct(ApiResponseModel):
    product_id: str
    picker_label: str
    picture_id: str
    thumbnail: str
    tags: tuple[str, ...]
    permalink: str


class PickerAttribute(ApiResponseModel):
    attribute_id: str
    template: str


class Picker(ApiResponseModel):
    picker_id: str
    picker_name: str
    products: tuple[PickerProduct, ...]
    tags: tuple[str, ...] | None = None
    attributes: tuple[PickerAttribute, ...]


class Picture(ApiResponseModel):
    id: str
    url: str
    suggested_for_picker: tuple[str, ...]
    max_width: int
    max_height: int


class MainFeature(ApiResponseModel):
    text: str
    type: str


class AttributeValue(ApiResponseModel):
    id: str
    name: str
    meta: FrozenDict[str, Any] | None = None


class Attribute(ApiResponseModel):
    id: str
    name: str
    value_id: str | None = None
    value_name: str
    values: tuple[AttributeValue, ...]
    meta: FrozenDict[str, Any] | None = None


class ShortDescription(ApiResponseModel):
    type: str
    content: str


class ProductSettings(ApiResponseModel):
    listing_strategy: str


class Product(ApiResponseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    status: str
    domain_id: str
    permalink: Url
    name: str
    family_name: str
    buy_box_winner: Any | None = None
    buy_box_winner_price_range: Any | None = None
    pickers: tuple[Picker, ...]
    pictures: tuple[Picture, ...]
    main_features: tuple[MainFeature, ...]
    attributes: tuple[Attribute, ...]
    short_description: ShortDescription
    parent_id: str
    children_ids: tuple[str, ...]
    settings: ProductSettings
    buy_box_activation_date: datetime
    date_created: datetime


def get_product(session: OAuth2Session, product_id: str) -> Product:
    """Query a specific product from Meli API."""
    url = PRODUCT_URL / product_id

    response = session.get(url.human_repr())
    response.raise_for_status()

    return Product.model_validate(response.json())
