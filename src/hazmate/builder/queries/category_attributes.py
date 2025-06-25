from typing import Any

from pydantic import BaseModel, ConfigDict
from requests_oauthlib import OAuth2Session

from hazmate.builder.queries.base import BASE_URL


class AttributeUnit(BaseModel):
    id: str
    name: str


class AttributeValue(BaseModel):
    id: str
    name: str
    metadata: dict[str, Any] | None = None


class CategoryAttribute(BaseModel):
    model_config = ConfigDict(frozen=True)

    attribute_group_id: str
    attribute_group_name: str
    hierarchy: str
    hint: str | None = None
    id: str
    name: str
    relevance: int
    tags: dict[str, Any]
    tooltip: str | None = None
    value_max_length: int | None = None
    value_type: str
    values: list[AttributeValue] | None = None
    allowed_units: list[AttributeUnit] | None = None
    default_unit: str | None = None


def get_category_attributes(
    session: OAuth2Session, category_id: str
) -> list[CategoryAttribute]:
    """Get attribute definitions for a specific category from Meli API.

    Args:
        session: The OAuth2 session to use.
        category_id: The category ID to get attributes for.

    Returns:
        List of CategoryAttribute models with attribute definitions.

    Raises:
        requests.HTTPError: If the API request fails
        pydantic.ValidationError: If the response doesn't match the expected schema
    """
    # Example of https://api.mercadolibre.com/categories/$CATEGORY_ID/attributes
    #     [{'attribute_group_id': 'OTHERS',
    #       'attribute_group_name': 'Outros',
    #       'hierarchy': 'PARENT_PK',
    #       'hint': "Informe a marca verdadeira do produto ou 'Genérica' se não tiver "
    #               'marca.',
    #       'id': 'BRAND',
    #       'name': 'Marca',
    #       'relevance': 1,
    #       'tags': {'catalog_listing_required': True,
    #                'catalog_required': True,
    #                'required': True},
    #       'value_max_length': 255,
    #       'value_type': 'string'},
    #      {'attribute_group_id': 'OTHERS',
    #       'attribute_group_name': 'Outros',
    #       'hierarchy': 'PARENT_PK',
    #       'id': 'PART_NUMBER',
    #       'name': 'Número de peça',
    #       'relevance': 1,
    #       'tags': {'catalog_required': True, 'required': True},
    #       'tooltip': 'Adicione essa informação para que os compradores encontrem o seu '
    #                  'anúncio mais rapidamente.',
    #       'value_max_length': 255,
    #       'value_type': 'string'},
    #      {'attribute_group_id': 'OTHERS',
    #       'attribute_group_name': 'Outros',
    #       'hierarchy': 'CHILD_PK',
    #       'id': 'COLOR',
    #       'name': 'Cor',
    #       'relevance': 1,
    #       'tags': {'allow_variations': True, 'defines_picture': True},
    #       'value_max_length': 255,
    #       'value_type': 'string',
    #       'values': [{'id': '52019', 'name': 'Verde-escuro'},
    #                  {'id': '283160', 'name': 'Azul-turquesa'},
    #                  {'id': '52022', 'name': 'Água'},
    #                  {'id': '283162', 'name': 'Índigo'},
    #                  {'id': '52036', 'name': 'Lavanda'},
    #                  {'id': '283163', 'name': 'Rosa-chiclete'},
    #                  {'id': '51998', 'name': 'Bordô'},
    #                  {'id': '52003', 'name': 'Nude'},
    #                  {'id': '52055', 'name': 'Branco'},
    #                  {'id': '283161', 'name': 'Azul-marinho'},
    #                  {'id': '52008', 'name': 'Creme'},
    #                  {'id': '52045', 'name': 'Rosa-pálido'},
    #                  {'id': '283153', 'name': 'Palha'},
    #                  {'id': '283150', 'name': 'Laranja-claro'},
    #                  {'id': '52028', 'name': 'Azul'},
    #                  {'id': '52043', 'name': 'Rosa-claro'},
    #                  {'id': '283148', 'name': 'Coral-claro'},
    #                  {'id': '283149', 'name': 'Coral'},
    #                  {'id': '52021', 'name': 'Azul-celeste'},
    #                  {'id': '52031', 'name': 'Azul-aço'},
    #                  {'id': '283156', 'name': 'Cáqui'},
    #                  {'id': '52001', 'name': 'Bege'},
    #                  {'id': '51993', 'name': 'Vermelho'},
    #                  {'id': '51996', 'name': 'Terracota'},
    #                  {'id': '283165', 'name': 'Cinza'},
    #                  {'id': '52035', 'name': 'Violeta'},
    #                  {'id': '283154', 'name': 'Marrom-claro'},
    #                  {'id': '52049', 'name': 'Preto'},
    #                  {'id': '283155', 'name': 'Marrom-escuro'},
    #                  {'id': '52053', 'name': 'Prateado'},
    #                  {'id': '52047', 'name': 'Violeta-escuro'},
    #                  {'id': '51994', 'name': 'Rosa'},
    #                  {'id': '52007', 'name': 'Amarelo'},
    #                  {'id': '283157', 'name': 'Verde-limão'},
    #                  {'id': '52012', 'name': 'Dourado-escuro'},
    #                  {'id': '52015', 'name': 'Verde-claro'},
    #                  {'id': '283151', 'name': 'Laranja-escuro'},
    #                  {'id': '52024', 'name': 'Azul-petróleo'},
    #                  {'id': '52051', 'name': 'Cinza-escuro'},
    #                  {'id': '283152', 'name': 'Chocolate'},
    #                  {'id': '52014', 'name': 'Verde'},
    #                  {'id': '283164', 'name': 'Dourado'},
    #                  {'id': '52000', 'name': 'Laranja'},
    #                  {'id': '52033', 'name': 'Azul-escuro'},
    #                  {'id': '52010', 'name': 'Ocre'},
    #                  {'id': '283158', 'name': 'Verde-musgo'},
    #                  {'id': '52005', 'name': 'Marrom'},
    #                  {'id': '52038', 'name': 'Lilás'},
    #                  {'id': '52042', 'name': 'Fúcsia'},
    #                  {'id': '338779', 'name': 'Ciano'},
    #                  {'id': '52029', 'name': 'Azul-claro'}]},
    #      {'attribute_group_id': 'OTHERS',
    #       'attribute_group_name': 'Outros',
    #       'hierarchy': 'FAMILY',
    #       'id': 'VEHICLE_TYPE',
    #       'name': 'Tipo de veículo',
    #       'relevance': 1,
    #       'tags': {},
    #       'value_type': 'list',
    #       'values': [{'id': '11377043', 'name': 'Carro/Caminhonete'},
    #                  {'id': '15279767', 'name': 'Moto/Quadriciclo'},
    #                  {'id': '13222040', 'name': 'Linha Pesada'},
    #                  {'id': '4369996', 'name': 'Agrícola'}]},
    #      {'allowed_units': [{'id': '"', 'name': '"'},
    #                         {'id': 'cm', 'name': 'cm'},
    #                         {'id': 'ft', 'name': 'ft'},
    #                         {'id': 'm', 'name': 'm'},
    #                         {'id': 'mm', 'name': 'mm'}],
    #       'attribute_group_id': 'OTHERS',
    #       'attribute_group_name': 'Outros',
    #       'default_unit': 'cm',
    #       'hierarchy': 'FAMILY',
    #       'id': 'PACKAGE_HEIGHT',
    #       'name': 'Altura da embalagem',
    #       'relevance': 1,
    #       'tags': {'hidden': True, 'read_only': True, 'variation_attribute': True},
    #       'value_max_length': 255,
    #       'value_type': 'number_unit'},
    #      {'allowed_units': [{'id': '"', 'name': '"'},
    #                         {'id': 'cm', 'name': 'cm'},
    #                         {'id': 'ft', 'name': 'ft'},
    #                         {'id': 'm', 'name': 'm'},
    #                         {'id': 'mm', 'name': 'mm'}],
    #       'attribute_group_id': 'OTHERS',
    #       'attribute_group_name': 'Outros',
    #       'default_unit': 'cm',
    #       'hierarchy': 'FAMILY',
    #       'id': 'PACKAGE_WIDTH',
    #       'name': 'Largura da embalagem',
    #       'relevance': 1,
    #       'tags': {'hidden': True, 'read_only': True, 'variation_attribute': True},
    #       'value_max_length': 255,
    #       'value_type': 'number_unit'},
    #      {'attribute_group_id': 'OTHERS',
    #       'attribute_group_name': 'Outros',
    #       'hierarchy': 'ITEM',
    #       'id': 'SEARCH_ENHANCEMENT_FIELDS',
    #       'name': 'Campos de aprimoramento de pesquisa',
    #       'relevance': 2,
    #       'tags': {'hidden': True, 'multivalued': True, 'read_only': True},
    #       'value_max_length': 255,
    #       'value_type': 'string'},
    #      {'attribute_group_id': 'OTHERS',
    #       'attribute_group_name': 'Outros',
    #       'hierarchy': 'ITEM',
    #       'id': 'PRODUCT_FEATURES',
    #       'name': 'Características do produto',
    #       'relevance': 2,
    #       'tags': {'hidden': True, 'multivalued': True, 'read_only': True},
    #       'value_type': 'list',
    #       'values': [{'id': '7435885', 'name': 'Contém líquido'},
    #                  {'id': '7435883', 'name': 'Frágil'},
    #                  {'id': '7435888', 'name': 'Com validade'},
    #                  {'id': '8847339', 'name': 'Sem validade'},
    #                  {'id': '7575917', 'name': 'Desinfetante e saneante'},
    #                  {'id': '7575924', 'name': 'MAPA'},
    #                  {'id': '7575923', 'name': 'Saúde e correlatos'},
    #                  {'id': '8721108', 'name': 'Volumoso'},
    #                  {'id': '10490116', 'name': 'Não voável'},
    #                  {'id': '12928414', 'name': 'Não rotacionável'},
    #                  {'id': '41722098', 'name': 'Dobrável'},
    #                  {'id': '52092586', 'name': 'Magnético'},
    #                  {'id': '52233302', 'name': 'Pode rolar'}]},
    #      {'attribute_group_id': 'OTHERS',
    #       'attribute_group_name': 'Outros',
    #       'hierarchy': 'ITEM',
    #       'id': 'IS_NEW_OFFER',
    #       'name': 'É nova oferta',
    #       'relevance': 2,
    #       'tags': {'hidden': True, 'read_only': True},
    #       'value_type': 'boolean',
    #       'values': [{'id': '242084', 'metadata': {'value': False}, 'name': 'Não'},
    #                  {'id': '242085', 'metadata': {'value': True}, 'name': 'Sim'}]}]

    url = BASE_URL / "categories" / category_id / "attributes"

    response = session.get(url.human_repr())
    response.raise_for_status()

    attributes_data = response.json()
    return [
        CategoryAttribute.model_validate(attr_data) for attr_data in attributes_data
    ]
