"""Example of how to use the categories query."""

from pprint import pprint

from hazmate_builder.app_config import AppConfig
from hazmate_builder.auth import start_oauth_session
from hazmate_builder.queries.base import SiteId
from hazmate_builder.queries.categories import get_categories


def main():
    config = AppConfig.from_dotenv(".env")

    with start_oauth_session(config) as session:
        response = get_categories(session, SiteId.BRAZIL)
        pprint(response)


if __name__ == "__main__":
    main()
