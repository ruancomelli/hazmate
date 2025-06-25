"""Main entry point for the hazmate builder package.

This script is used to build the hazmate dataset.
"""

from pathlib import Path
from pprint import pformat

from rich.progress import Progress

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
from hazmate.utils.oauth import OAuth2Session


def main():
    auth_config = AuthConfig.from_dotenv(".env")
    collector_config = CollectorConfig.from_yaml(Path("collector-config.yaml"))

    with start_oauth_session(auth_config) as session:
        api_categories_data = _collect_categories_with_subcategories_and_attributes(
            session
        )

        _validate_all_categories_in_config_exist(collector_config, api_categories_data)
        _validate_all_categories_are_in_config(collector_config, api_categories_data)


def _collect_categories_with_subcategories_and_attributes(
    session: OAuth2Session,
) -> list[tuple[CategoryDetail, list[tuple[ChildCategory, list[CategoryAttribute]]]]]:
    """Collect all categories with their subcategories and attributes."""
    result: list[
        tuple[CategoryDetail, list[tuple[ChildCategory, list[CategoryAttribute]]]]
    ] = []

    categories = list(get_categories(session, SiteId.BRAZIL))

    with Progress() as progress:
        main_task = progress.add_task("Collecting categories...", total=len(categories))

        for category_ref in categories:
            category = get_category(session, category_ref.id)

            subcategories: list[tuple[ChildCategory, list[CategoryAttribute]]] = []

            if category.children_categories:
                child_task = progress.add_task(
                    f"[cyan]Collecting children of {category_ref.name}[/cyan]",
                    total=len(category.children_categories),
                )

                for child_category in category.children_categories:
                    attributes = get_category_attributes(session, child_category.id)
                    subcategories.append((child_category, attributes))
                    progress.update(child_task, advance=1)

                progress.remove_task(child_task)

            result.append((category, subcategories))
            progress.update(main_task, advance=1)

    return result


def _validate_all_categories_in_config_exist(
    config: CollectorConfig,
    categories: list[
        tuple[CategoryDetail, list[tuple[ChildCategory, list[CategoryAttribute]]]]
    ],
) -> None:
    """Validate that all categories in the config exist in the API response list."""
    # Build lookup dictionaries using IDs as keys
    api_categories_by_id: dict[str, CategoryDetail | ChildCategory] = {}

    for ref_category, subcategories in categories:
        api_categories_by_id[ref_category.id] = ref_category
        for subcategory, _ in subcategories:
            api_categories_by_id[subcategory.id] = subcategory

    config_categories = [*config.categories.include, *config.categories.exclude]

    with Progress() as progress:
        task = progress.add_task(
            "Validating config categories exist...", total=len(config_categories)
        )

        for category_config in config_categories:
            if category_config.id not in api_categories_by_id:
                raise ValueError(
                    f"Category {category_config.id} '{category_config.name}' not found in categories"
                )

            category = api_categories_by_id[category_config.id]
            if category.name != category.name:
                raise ValueError(
                    f"Category {category.id} has different name in config: {category.name} != {category.name}"
                )

            progress.update(task, advance=1)


def _validate_all_categories_are_in_config(
    config: CollectorConfig,
    categories: list[
        tuple[CategoryDetail, list[tuple[ChildCategory, list[CategoryAttribute]]]]
    ],
) -> None:
    """Validate that all categories in the config are in the categories list, either included or excluded."""
    config_categories_ids = {
        category.id
        for category in (*config.categories.include, *config.categories.exclude)
    }

    # Extract all categories from the API data
    api_categories_list = [category for category, _ in categories]

    with Progress() as progress:
        task = progress.add_task(
            "Validating all API categories are in config...",
            total=len(api_categories_list),
        )

        missing_categories: list[tuple[str, str]] = []

        for api_category in api_categories_list:
            if api_category.id not in config_categories_ids:
                missing_categories.append((api_category.id, api_category.name))
            progress.update(task, advance=1)

        if missing_categories:
            raise ValueError(
                f"The following categories were not found in the config - please either include or exclude them:\n{pformat(missing_categories)}"
            )


if __name__ == "__main__":
    main()
