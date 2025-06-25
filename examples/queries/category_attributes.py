"""Example of how to use the category query."""

from pprint import pprint

from hazmate.builder.auth_config import AuthConfig
from hazmate.builder.auth import start_oauth_session
from hazmate.builder.queries.category_attributes import get_category_attributes


def main():
    config = AuthConfig.from_dotenv(".env")

    with start_oauth_session(config) as session:
        response = get_category_attributes(session, "MLB5672")
        pprint(response)


if __name__ == "__main__":
    main()
