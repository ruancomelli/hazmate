"""Example of how to use the categories query."""

from asyncer import runnify
from rich import print

from hazmate.input_datasets.auth import start_oauth_session
from hazmate.input_datasets.auth_config import AuthConfig
from hazmate.input_datasets.queries.base import SiteId
from hazmate.input_datasets.queries.categories import get_categories


@runnify
async def main():
    config = AuthConfig.from_dotenv(".env")

    async with start_oauth_session(config) as session:
        categories = await get_categories(session, SiteId.BRAZIL)
        print(f"[bold green]Found {len(categories)} categories:[/bold green]")
        for category in categories:
            print(f"[cyan]•[/cyan] {category.name} ([blue]{category.id}[/blue])")


if __name__ == "__main__":
    main()
