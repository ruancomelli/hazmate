"""Example of getting all subcategories and their attributes."""

from asyncer import runnify
from rich import print

from hazmate.input_datasets.auth import start_oauth_session
from hazmate.input_datasets.auth_config import AuthConfig
from hazmate.input_datasets.queries.base import SiteId
from hazmate.input_datasets.queries.categories import get_categories
from hazmate.input_datasets.queries.category import get_category
from hazmate.input_datasets.queries.category_attributes import get_category_attributes


@runnify
async def main():
    config = AuthConfig.from_dotenv(".env")

    async with start_oauth_session(config) as session:
        total_subcategories_count = 0
        total_items_count = 0

        categories = await get_categories(session, SiteId.BRAZIL)

        for category_ref in categories:
            category = await get_category(session, category_ref.id)

            subcategories_count = len(category.children_categories)
            items_count = category.total_items_in_this_category

            print(
                f"[bold blue]{category.name}[/bold blue] ([cyan]{subcategories_count} children[/cyan] | [green]{items_count} items[/green])"
            )

            total_subcategories_count += subcategories_count
            total_items_count += items_count

            for child_category in category.children_categories:
                print(
                    f"    [blue]{child_category.name}[/blue] ([green]{child_category.total_items_in_this_category} items[/green])"
                )

                attributes = await get_category_attributes(session, child_category.id)
                for attribute in attributes:
                    print(f"        [cyan]• {attribute.name}[/cyan]")

        print("\n[bold green]Summary:[/bold green]")
        print(f"[cyan]Total categories:[/cyan] {len(categories)}")
        print(f"[cyan]Total subcategories:[/cyan] {total_subcategories_count}")
        print(f"[cyan]Total items:[/cyan] {total_items_count:,}")


if __name__ == "__main__":
    main()
