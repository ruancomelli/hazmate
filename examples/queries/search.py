"""Example of how to use the search query."""

from pprint import pprint

from asyncer import runnify

from hazmate.input_datasets.auth import start_oauth_session
from hazmate.input_datasets.auth_config import AuthConfig
from hazmate.input_datasets.queries.base import SiteId
from hazmate.input_datasets.queries.search import search_products


@runnify
async def main():
    config = AuthConfig.from_dotenv(".env")

    async with start_oauth_session(config) as session:
        response = await search_products(
            session,
            site_id=SiteId.BRAZIL,
            query="dinossauro",
        )
        pprint(response.model_dump())


if __name__ == "__main__":
    main()
