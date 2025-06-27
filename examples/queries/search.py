"""Example of how to use the search query."""

from asyncer import runnify
from rich import print

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
        print(f"[bold green]Found {len(response.results)} products:[/bold green]")
        for product in response.results[:5]:  # Show first 5
            print(f"[cyan]•[/cyan] {product.name} ([blue]{product.id}[/blue])")


if __name__ == "__main__":
    main()
