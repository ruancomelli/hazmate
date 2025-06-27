"""Example of how to use the category query."""

from asyncer import runnify
from rich import print

from hazmate.input_datasets.auth import start_oauth_session
from hazmate.input_datasets.auth_config import AuthConfig
from hazmate.input_datasets.queries.category import get_category


@runnify
async def main():
    config = AuthConfig.from_dotenv(".env")

    async with start_oauth_session(config) as session:
        category = await get_category(session, "MLB5672")
        print(f"[bold blue]Category:[/bold blue] {category.name}")
        print(f"[cyan]ID:[/cyan] {category.id}")
        print(f"[cyan]Children:[/cyan] {len(category.children_categories)}")
        print(f"[cyan]Total items:[/cyan] {category.total_items_in_this_category}")


if __name__ == "__main__":
    main()
