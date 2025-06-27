from asyncer import runnify
from rich import print

from hazmate.input_datasets.auth import start_oauth_session
from hazmate.input_datasets.auth_config import AuthConfig
from hazmate.input_datasets.queries.base import SiteId
from hazmate.input_datasets.queries.search import search_products_paginated
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
            print(f"[bold blue]Page {index}:[/bold blue]")
            for subindex, result in enumerate(response.results):
                print(f"  [cyan]{index}.{subindex}[/cyan] -> {result.name}")


if __name__ == "__main__":
    main()
