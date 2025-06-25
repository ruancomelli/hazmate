from pydantic import ConfigDict

from hazmate.builder.queries.base import BASE_URL, ApiResponseModel, SiteId
from hazmate.utils.oauth import OAuth2Session


class CategorySimple(ApiResponseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str


def get_categories(session: OAuth2Session, site_id: SiteId) -> list[CategorySimple]:
    """Get all categories for a specific site from Meli API.

    Args:
        session: The OAuth2 session to use.
        site_id: The site to get categories for.

    Returns:
        List of Category models.

    Raises:
        requests.HTTPError: If the API request fails
        pydantic.ValidationError: If the response doesn't match the expected schema
    """
    # Example API response:
    # [{'id': 'MLB5672', 'name': 'Acessórios para Veículos'},
    #  {'id': 'MLB271599', 'name': 'Agro'},
    #  {'id': 'MLB1403', 'name': 'Alimentos e Bebidas'},
    #  {'id': 'MLB1071', 'name': 'Animais'},
    #  {'id': 'MLB1367', 'name': 'Antiguidades e Coleções'},
    #  {'id': 'MLB1368', 'name': 'Arte, Papelaria e Armarinho'},
    #  {'id': 'MLB1384', 'name': 'Bebês'},
    #  {'id': 'MLB1246', 'name': 'Beleza e Cuidado Pessoal'},
    #  {'id': 'MLB1132', 'name': 'Brinquedos e Hobbies'},
    #  {'id': 'MLB1430', 'name': 'Calçados, Roupas e Bolsas'},
    #  {'id': 'MLB1039', 'name': 'Câmeras e Acessórios'},
    #  {'id': 'MLB1743', 'name': 'Carros, Motos e Outros'},
    #  {'id': 'MLB1574', 'name': 'Casa, Móveis e Decoração'},
    #  {'id': 'MLB1051', 'name': 'Celulares e Telefones'},
    #  {'id': 'MLB1500', 'name': 'Construção'},
    #  {'id': 'MLB5726', 'name': 'Eletrodomésticos'},
    #  {'id': 'MLB1000', 'name': 'Eletrônicos, Áudio e Vídeo'},
    #  {'id': 'MLB1276', 'name': 'Esportes e Fitness'},
    #  {'id': 'MLB263532', 'name': 'Ferramentas'},
    #  {'id': 'MLB12404', 'name': 'Festas e Lembrancinhas'},
    #  {'id': 'MLB1144', 'name': 'Games'},
    #  {'id': 'MLB1459', 'name': 'Imóveis'},
    #  {'id': 'MLB1499', 'name': 'Indústria e Comércio'},
    #  {'id': 'MLB1648', 'name': 'Informática'},
    #  {'id': 'MLB218519', 'name': 'Ingressos'},
    #  {'id': 'MLB1182', 'name': 'Instrumentos Musicais'},
    #  {'id': 'MLB3937', 'name': 'Joias e Relógios'},
    #  {'id': 'MLB1196', 'name': 'Livros, Revistas e Comics'},
    #  {'id': 'MLB1168', 'name': 'Música, Filmes e Seriados'},
    #  {'id': 'MLB264586', 'name': 'Saúde'},
    #  {'id': 'MLB1540', 'name': 'Serviços'},
    #  {'id': 'MLB1953', 'name': 'Mais Categorias'}]
    url = BASE_URL / "sites" / site_id.value / "categories"

    response = session.get(url.human_repr())
    response.raise_for_status()

    categories_data = response.json()
    return [
        CategorySimple.model_validate(category_data)
        for category_data in categories_data
    ]
