"""Example of getting all subcategories and their attributes."""

from hazmate.input_datasets.auth import start_oauth_session
from hazmate.input_datasets.auth_config import AuthConfig
from hazmate.input_datasets.queries.base import SiteId
from hazmate.input_datasets.queries.categories import get_categories
from hazmate.input_datasets.queries.category import get_category
from hazmate.input_datasets.queries.category_attributes import get_category_attributes


def main():
    config = AuthConfig.from_dotenv(".env")

    with start_oauth_session(config) as session:
        total_subcategories_count = 0
        total_items_count = 0

        categories = list(get_categories(session, SiteId.BRAZIL))

        for category_ref in categories:
            category = get_category(session, category_ref.id)

            subcategories_count = len(category.children_categories)
            items_count = category.total_items_in_this_category

            print(
                f"{category.name} ({subcategories_count} children | {items_count} items)"
            )

            total_subcategories_count += subcategories_count
            total_items_count += items_count

            for child_category in category.children_categories:
                print(
                    f"    {child_category.name} ({child_category.total_items_in_this_category} items)"
                )

                for attribute in get_category_attributes(session, child_category.id):
                    print(f"        {attribute.name}")

        print(f"Total categories: {len(categories)}")
        print(f"Total subcategories: {total_subcategories_count}")
        print(f"Total items: {total_items_count:,}")


if __name__ == "__main__":
    main()
