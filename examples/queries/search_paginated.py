from hazmate.builder.auth import start_oauth_session
from hazmate.builder.auth_config import AuthConfig
from hazmate.builder.queries.base import SiteId
from hazmate.builder.queries.search import search_products_paginated


def main():
    config = AuthConfig.from_dotenv(".env")

    with start_oauth_session(config) as session:
        for index, response in enumerate(
            search_products_paginated(
                session,
                "dinossauro",
                SiteId.BRAZIL,
            ),
        ):
            print(index, "->", response.results[0].name)


if __name__ == "__main__":
    main()
