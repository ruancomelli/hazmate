"""Example of how to use the categories query."""

from pprint import pprint

from asyncer import runnify

from hazmate.input_datasets.auth import start_oauth_session
from hazmate.input_datasets.auth_config import AuthConfig
from hazmate.input_datasets.queries.base import SiteId
from hazmate.input_datasets.queries.categories import get_categories


@runnify
async def main():
    config = AuthConfig.from_dotenv(".env")

    async with start_oauth_session(config) as session:
        categories = await get_categories(session, SiteId.BRAZIL)
        pprint(categories)


if __name__ == "__main__":
    main()
