"""Example of how to use the category attributes query."""

from asyncer import runnify
from rich import print

from hazmate.input_datasets.auth import start_oauth_session
from hazmate.input_datasets.auth_config import AuthConfig
from hazmate.input_datasets.queries.category_attributes import get_category_attributes


@runnify
async def main():
    config = AuthConfig.from_dotenv(".env")

    async with start_oauth_session(config) as session:
        attributes = await get_category_attributes(session, "MLB5672")
        print(
            f"[bold green]Found {len(attributes)} attributes for category MLB5672:[/bold green]"
        )
        for attribute in attributes:
            print(f"[cyan]•[/cyan] {attribute.name} ([blue]{attribute.id}[/blue])")


if __name__ == "__main__":
    main()
