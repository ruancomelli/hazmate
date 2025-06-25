"""Example of how to use the category query."""

from pprint import pprint

from hazmate_builder.app_config import AppConfig
from hazmate_builder.auth import start_oauth_session
from hazmate_builder.queries.category_attributes import get_category_attributes


def main():
    config = AppConfig.from_dotenv(".env")

    with start_oauth_session(config) as session:
        response = get_category_attributes(session, "MLB5672")
        pprint(response)


if __name__ == "__main__":
    main()
