"""Example of how to use the category query."""

from pprint import pprint

from asyncer import runnify

from hazmate.input_datasets.auth import start_oauth_session
from hazmate.input_datasets.auth_config import AuthConfig
from hazmate.input_datasets.queries.category_attributes import get_category_attributes


@runnify
async def main():
    config = AuthConfig.from_dotenv(".env")

    async with start_oauth_session(config) as session:
        response = await get_category_attributes(session, "MLB5672")
        pprint(response)


if __name__ == "__main__":
    main()
