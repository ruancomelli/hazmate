from typing import Any

from hazmate_builder.app_config import AppConfig
from hazmate_builder.auth import start_oauth_session
from hazmate_builder.queries.base import PaginatedReponseJson, paginate
from pprint import pprint


def main():
    config = AppConfig.from_dotenv(".env")


    with start_oauth_session(config) as session:
        response = session.get(
            "https://api.mercadolibre.com/products/search",
            params={"q": "dinossauro", "site_id": "MLB"},
        )
        pprint(response.json())

    # def requester(offset: int) -> PaginatedReponseJson[dict[str, Any]]:
    #     response = session.get(
    #         "https://api.mercadolibre.com/products/search",
    #         params={"q": "carrinho de bebe", "site_id": "MLB", "offset": offset},
    #     )
    #     return response.json()

    # with start_oauth_session(config) as session:
    #     for count, product in enumerate(paginate(requester)):
    #         print(count, "->", product["name"])


if __name__ == "__main__":
    main()
