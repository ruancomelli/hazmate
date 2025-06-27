"""Example of getting all subcategories and their attributes."""

from rich.progress import Progress

from hazmate.input_datasets.auth import start_oauth_session
from hazmate.input_datasets.auth_config import AuthConfig
from hazmate.input_datasets.queries.base import SiteId
from hazmate.input_datasets.queries.categories import get_categories
from hazmate.input_datasets.queries.category import get_category
from hazmate.input_datasets.queries.category_attributes import get_category_attributes


def main():
    config = AuthConfig.from_dotenv(".env")

    all_attribute_names: set[str] = set()

    with start_oauth_session(config) as session:
        # Get all categories first to know the total count
        categories = list(get_categories(session, SiteId.BRAZIL))

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
