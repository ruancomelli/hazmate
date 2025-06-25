"""Example of how to use the search query."""

from pprint import pprint

from hazmate_builder.app_config import AppConfig
from hazmate_builder.auth import start_oauth_session
from hazmate_builder.queries.base import SiteId
from hazmate_builder.queries.search import search_products


def main():
    config = AppConfig.from_dotenv(".env")

    with start_oauth_session(config) as session:
        response = search_products(
            session,
            query="dinossauro",
            site_id=SiteId.BRAZIL,
        )
        pprint(response)


if __name__ == "__main__":
    main()
