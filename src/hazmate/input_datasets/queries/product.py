from datetime import datetime

from pydantic import ConfigDict, field_validator
from pydantic import HttpUrl as Url

from hazmate.input_datasets.queries.base import BASE_URL, ApiResponseModel
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
    suggested_for_picker: tuple[str, ...] | None = None
    max_width: int | None = None
    max_height: int | None = None


class MainFeature(ApiResponseModel):
    text: str
    type: str


class AttributeValue(ApiResponseModel):
    id: str
    name: str


class Attribute(ApiResponseModel):
    id: str
    name: str
    value_id: str | None = None
    value_name: str
    values: tuple[AttributeValue, ...] | None = None


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
    permalink: Url | None = None
    name: str
    family_name: str
    pickers: tuple[Picker, ...] | None = None
    pictures: tuple[Picture, ...] | None = None
    main_features: tuple[MainFeature, ...] | None = None
    attributes: tuple[Attribute, ...]
    short_description: ShortDescription
    parent_id: str | None = None
    children_ids: tuple[str, ...] | None = None
    settings: ProductSettings | None = None
    date_created: datetime

    @field_validator("permalink", mode="before")
    def validate_permalink(cls, v: str | None) -> Url | None:
        return Url(v) if v else None


async def get_product(session: OAuth2Session, product_id: str) -> Product:
    """Query a specific product from Meli API."""
    # Example of https://api.mercadolibre.com/products/$PRODUCT_ID
    #     {'attributes': [{'id': 'BRAND',
    #                     'name': 'Marca',
    #                     'value_id': '45462093',
    #                     'value_name': 'Ladai',
    #                     'values': [{'id': '45462093', 'name': 'Ladai'}]},
    #                     {'id': 'MANUFACTURER',
    #                     'name': 'Fabricante',
    #                     'value_id': '40609884',
    #                     'value_name': 'DINO STATE',
    #                     'values': [{'id': '40609884', 'name': 'DINO STATE'}]},
    #                     {'id': 'COLLECTION',
    #                     'name': 'Coleção',
    #                     'value_id': '50140828',
    #                     'value_name': 'dinossauro perigoso',
    #                     'values': [{'id': '50140828', 'name': 'dinossauro perigoso'}]},
    #                     {'id': 'HEIGHT',
    #                     'name': 'Altura',
    #                     'value_id': '1006867',
    #                     'value_name': '15 cm',
    #                     'values': [{'id': '1006867', 'name': '15 cm'}]},
    #                     {'id': 'MATERIALS',
    #                     'name': 'Materiais',
    #                     'value_id': '2748302',
    #                     'value_name': 'Plástico',
    #                     'values': [{'id': '2748302', 'name': 'Plástico'}]},
    #                     {'id': 'IS_COLLECTIBLE',
    #                     'meta': {'value': True},
    #                     'name': 'É colecionável',
    #                     'value_id': '242085',
    #                     'value_name': 'Sim',
    #                     'values': [{'id': '242085',
    #                                 'meta': {'value': True},
    #                                 'name': 'Sim'}]},
    #                     {'id': 'INCLUDES_ACCESSORIES',
    #                     'meta': {'value': False},
    #                     'name': 'Inclui acessórios',
    #                     'value_id': '242084',
    #                     'value_name': 'Não',
    #                     'values': [{'id': '242084',
    #                                 'meta': {'value': False},
    #                                 'name': 'Não'}]}],
    #     'authorized_stores': None,
    #     'buy_box_winner': None,
    #     'catalog_product_id': 'MLB47606852',
    #     'children_ids': [],
    #     'date_created': '2025-03-31T17:30:27Z',
    #     'description_pictures': [],
    #     'disclaimers': [],
    #     'domain_id': 'MLB-ACTION_FIGURES',
    #     'enhanced_content': None,
    #     'experiments': {},
    #     'family_name': 'Dinossauro Tyrannosaurus Rex - Dinossauro Som/Perigoso',
    #     'grouper_id': None,
    #     'id': 'MLB47606852',
    #     'last_updated': '2025-03-31T17:40:42Z',
    #     'main_features': [{'metadata': {},
    #                         'text': 'É feito de plástico.',
    #                         'type': 'key_value'},
    #                     {'metadata': {},
    #                         'text': 'Boneco colecionável.',
    #                         'type': 'key_value'}],
    #     'name': 'Dinossauro Tyrannosaurus Rex - Dinossauro Som/Perigoso',
    #     'parent_id': None,
    #     'pdp_types': ['traditional'],
    #     'permalink': '',
    #     'pickers': None,
    #     'pictures': [{'id': '929518-MLA83444693269_032025',
    #                 'max_height': 764,
    #                 'max_width': 817,
    #                 'source_metadata': None,
    #                 'suggested_for_picker': None,
    #                 'tags': ['CAROUSEL'],
    #                 'url': 'https://http2.mlstatic.com/D_NQ_NP_929518-MLA83444693269_032025-F.jpg'},
    #                 {'id': '610995-MLA83153900696_032025',
    #                 'max_height': 741,
    #                 'max_width': 782,
    #                 'source_metadata': None,
    #                 'suggested_for_picker': None,
    #                 'tags': ['CAROUSEL'],
    #                 'url': 'https://http2.mlstatic.com/D_NQ_NP_610995-MLA83153900696_032025-F.jpg'}],
    #     'presale_info': None,
    #     'quality_type': 'COMPLETE',
    #     'release_info': None,
    #     'settings': {'base_site_product_id': None,
    #                 'content': 'fixed',
    #                 'exclusive': False,
    #                 'listing_strategy': 'catalog_required',
    #                 'with_enhanced_pictures': False},
    #     'short_description': {'content': 'Mergulhe na era pré-histórica com o '
    #                                     'dinossauro Tyrannosaurus Rex da coleção '
    #                                     'Dangerous Dino de Ladai. Este '
    #                                     'impressionante modelo de 15 cm, feito de '
    #                                     'plástico de alta qualidade, é uma peça '
    #                                     'indispensável para amantes e colecionadores '
    #                                     'de dinossauros. Seu design detalhado e '
    #                                     'realista captura a essência desse temido '
    #                                     'predador, tornando-o uma atração para '
    #                                     'crianças e adultos. \n'
    #                                     ' \n'
    #                                     ' O Tyrannosaurus Rex não é apenas uma '
    #                                     'figura de ação, mas também emite sons que '
    #                                     'simulam seu rugido característico, '
    #                                     'proporcionando uma experiência interativa '
    #                                     'que estimula a imaginação. Ideal para '
    #                                     'recriar aventuras emocionantes ou para '
    #                                     'exibir em sua coleção, esse dinossauro é um '
    #                                     'verdadeiro tesouro para quem aprecia '
    #                                     'história natural e fantasia. \n'
    #                                     ' \n'
    #                                     ' Com seu tamanho perfeito, o Tyrannosaurus '
    #                                     'Rex se adapta a qualquer espaço, seja em '
    #                                     'uma prateleira, mesa ou como parte de um '
    #                                     'jogo. Não perca a chance de adicionar esse '
    #                                     'dinossauro perigoso à sua coleção e reviver '
    #                                     'a emoção da era dos gigantes.',
    #                         'type': 'plaintext'},
    #     'status': 'active',
    #     'tags': [],
    #     'type': 'catalog_product',
    #     'user_product': None}

    url = PRODUCT_URL / product_id

    response = await session.get(url)
    response.raise_for_status()

    return Product.model_validate(response.json())
