"""Example of how to use the categories query."""

from pprint import pprint

from hazmate.builder.auth import start_oauth_session
from hazmate.builder.auth_config import AuthConfig
from hazmate.builder.queries.base import SiteId
from hazmate.builder.queries.categories import iter_categories


def main():
    config = AuthConfig.from_dotenv(".env")

    with start_oauth_session(config) as session:
        categories = list(iter_categories(session, SiteId.BRAZIL))
        pprint(categories)


if __name__ == "__main__":
    main()
