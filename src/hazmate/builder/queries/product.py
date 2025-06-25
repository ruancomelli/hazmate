from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict
from pydantic import HttpUrl as Url
from requests_oauthlib import OAuth2Session

from hazmate.builder.queries.base import BASE_URL

PRODUCT_URL = BASE_URL / "products"


class PickerProduct(BaseModel):
    product_id: str
    picker_label: str
    picture_id: str
    thumbnail: str
    tags: list[str]
    permalink: str


class PickerAttribute(BaseModel):
    attribute_id: str
    template: str


class Picker(BaseModel):
    picker_id: str
    picker_name: str
    products: list[PickerProduct]
    tags: Optional[Any] = None
    attributes: list[PickerAttribute]


class Picture(BaseModel):
    id: str
    url: str
    suggested_for_picker: list[str]
    max_width: int
    max_height: int


class MainFeature(BaseModel):
    text: str
    type: str


class AttributeValue(BaseModel):
    id: str
    name: str
    meta: Optional[dict[str, Any]] = None


class Attribute(BaseModel):
    id: str
    name: str
    value_id: Optional[str] = None
    value_name: str
    values: list[AttributeValue]
    meta: Optional[dict[str, Any]] = None


class ShortDescription(BaseModel):
    type: str
    content: str


class ProductSettings(BaseModel):
    listing_strategy: str


class Product(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    status: str
    domain_id: str
    permalink: Url
    name: str
    family_name: str
    buy_box_winner: Optional[Any] = None
    buy_box_winner_price_range: Optional[Any] = None
    pickers: list[Picker]
    pictures: list[Picture]
    main_features: list[MainFeature]
    attributes: list[Attribute]
    short_description: ShortDescription
    parent_id: str
    children_ids: list[str]
    settings: ProductSettings
    buy_box_activation_date: datetime
    date_created: datetime


def get_product(session: OAuth2Session, product_id: str) -> Product:
    """Query a specific product from Meli API."""
    url = PRODUCT_URL / product_id

    response = session.get(url.human_repr())
    response.raise_for_status()

    return Product.model_validate(response.json())
