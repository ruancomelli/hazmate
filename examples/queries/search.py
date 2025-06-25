"""Example of how to use the search query."""

from pprint import pprint

from hazmate.builder.auth import start_oauth_session
from hazmate.builder.auth_config import AuthConfig
from hazmate.builder.queries.base import SiteId
from hazmate.builder.queries.search import search_items


def main():
    config = AuthConfig.from_dotenv(".env")

    with start_oauth_session(config) as session:
        response = search_items(
            session,
            query="dinossauro",
            site_id=SiteId.BRAZIL,
        )
        pprint(response)


if __name__ == "__main__":
    main()
