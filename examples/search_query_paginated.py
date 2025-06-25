from hazmate_builder.app_config import AppConfig
from hazmate_builder.auth import start_oauth_session
from hazmate_builder.queries.base import SiteId
from hazmate_builder.queries.search import search_products_paginated


def main():
    config = AppConfig.from_dotenv(".env")

    with start_oauth_session(config) as session:
        for index, response in enumerate(
            search_products_paginated(session, "carrinho de bebe", SiteId.BRAZIL),
        ):
            print(index, "->", response.results[0].name)


if __name__ == "__main__":
    main()
