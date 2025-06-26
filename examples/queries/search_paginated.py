from asyncer import runnify

from hazmate.builder.auth import start_oauth_session
from hazmate.builder.auth_config import AuthConfig
from hazmate.builder.queries.base import SiteId
from hazmate.builder.queries.search import search_products_paginated
from hazmate.utils.async_itertools import aenumerate


@runnify
async def main():
    config = AuthConfig.from_dotenv(".env")

    async with start_oauth_session(config) as session:
        async for index, response in aenumerate(
            search_products_paginated(
                session,
                site_id=SiteId.BRAZIL,
                query="dinossauro",
            ),
        ):
            for subindex, result in enumerate(response.results):
                print(f"{index}.{subindex} -> {result.name}")


if __name__ == "__main__":
    main()
