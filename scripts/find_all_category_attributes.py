"""Example of getting all subcategories and their attributes."""

from pathlib import Path

import requests_cache

CACHE_DIR = Path(".cache")
# Install the cache before importing any modules that use the requests library
# I'm not sure why this is necessary, but it is - without it, the cache is not used
requests_cache.install_cache(str(CACHE_DIR / "requests"))

from rich.progress import Progress

from hazmate.builder.auth import start_oauth_session
from hazmate.builder.auth_config import AuthConfig
from hazmate.builder.queries.base import SiteId
from hazmate.builder.queries.categories import iter_categories
from hazmate.builder.queries.category import get_category
from hazmate.builder.queries.category_attributes import get_category_attributes


def main():
    config = AuthConfig.from_dotenv(".env")

    all_attribute_names: set[str] = set()

    with start_oauth_session(config) as session:
        # Get all categories first to know the total count
        categories = list(iter_categories(session, SiteId.BRAZIL))

        with Progress() as progress:
            for category_ref in progress.track(
                categories, description="Processing categories..."
            ):
                category = get_category(session, category_ref.id)

                if category.children_categories:
                    # Add sub-task for child categories
                    child_task = progress.add_task(
                        f"[cyan]Processing children of {category_ref.name}[/cyan]",
                        total=len(category.children_categories),
                    )

                    for child_category in category.children_categories:
                        for attribute in get_category_attributes(
                            session, child_category.id
                        ):
                            all_attribute_names.add(attribute.name)

                        progress.update(child_task, advance=1)

                    progress.remove_task(child_task)

    print(f"Total attributes: {len(all_attribute_names)}")
    for attribute_name in sorted(all_attribute_names, key=str.casefold):
        print(attribute_name)


if __name__ == "__main__":
    main()
