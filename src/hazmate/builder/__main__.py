"""Main entry point for the hazmate builder package.

This script is used to build the hazmate dataset.
"""

from pathlib import Path

from requests_oauthlib import OAuth2Session

from hazmate.builder.auth import start_oauth_session
from hazmate.builder.auth_config import AuthConfig
from hazmate.builder.collector_config import CollectorConfig
from hazmate.builder.queries.base import SiteId
from hazmate.builder.queries.categories import get_categories
from hazmate.builder.queries.category import CategoryDetail, ChildCategory, get_category
from hazmate.builder.queries.category_attributes import (
    CategoryAttribute,
    get_category_attributes,
)


def main():
    auth_config = AuthConfig.from_dotenv(".env")
    collector_config = CollectorConfig.from_yaml(Path("collector-config.yaml"))

    with start_oauth_session(auth_config) as session:
        # Example usage of the new function
        categories_data = _collect_categories_with_subcategories_and_attributes(session)

        # Print summary
        print(f"Collected {len(categories_data)} categories")
        for category, subcategories in categories_data:
            print(f"{category.name}: {len(subcategories)} subcategories")

        # Original code for other functionality
        for category_config in collector_config.categories:
            for category in category_config.include:
                print(category)


def _collect_categories_with_subcategories_and_attributes(
    session: OAuth2Session,
) -> list[tuple[CategoryDetail, list[tuple[ChildCategory, list[CategoryAttribute]]]]]:
    """
    Collect all categories with their subcategories and attributes.

    Returns:
        list[tuple[category, list[tuple[subcategory, attributes]]]]:
        A list where each element is a tuple of (category, subcategory_data).
        subcategory_data is a list of tuples (subcategory, attributes).
    """
    result = []

    categories = get_categories(session, SiteId.BRAZIL)

    for category_ref in categories:
        category = get_category(session, category_ref.id)

        subcategory_data = []
        for child_category in category.children_categories:
            attributes = get_category_attributes(session, child_category.id)
            subcategory_data.append((child_category, attributes))

        result.append((category, subcategory_data))

    return result


if __name__ == "__main__":
    main()
