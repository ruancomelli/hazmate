"""Main entry point for the hazmate builder package.

This script is used to build the hazmate dataset.
"""

import csv
from collections.abc import Iterator
from pathlib import Path
from pprint import pformat
from typing import Annotated

import typer
from asyncer import runnify
from requests.exceptions import HTTPError
from rich.progress import Progress

from hazmate.builder.auth import start_oauth_session
from hazmate.builder.auth_config import AuthConfig
from hazmate.builder.collector_config import CollectorConfig
from hazmate.builder.input_dataset import InputDatasetItem
from hazmate.builder.queries.base import SiteId
from hazmate.builder.queries.categories import iter_categories
from hazmate.builder.queries.category import CategoryDetail, ChildCategory, get_category
from hazmate.builder.queries.category_attributes import (
    CategoryAttribute,
    get_category_attributes,
)
from hazmate.builder.queries.product import get_product
from hazmate.builder.queries.search import search_products_paginated
from hazmate.utils.oauth import OAuth2Session

QUERY_SIZE_LIMIT = 100
MAX_CONSECUTIVE_FAILURES = 10  # Avoid infinite loops if many products fail
OUTPUT_DIR = Path("data")

app = typer.Typer()


@app.command()
@runnify
async def main(
    target_size: Annotated[
        int,
        typer.Option(
            "--target-size",
            "-t",
            help="Target size of the dataset",
        ),
    ] = 100_000,
    config_path: Annotated[
        Path,
        typer.Option(
            "--config",
            "-c",
            help="Path to the collector config file",
        ),
    ] = Path("collector-config.yaml"),
    output_name: Annotated[
        str,
        typer.Option(
            "--output-name",
            "-o",
            help="Name of the output file",
        ),
    ] = "input_dataset.csv",
):
    auth_config = AuthConfig.from_dotenv(".env")
    collector_config = CollectorConfig.from_yaml(config_path)

    with start_oauth_session(auth_config) as session:
        api_categories_data = _collect_categories_with_subcategories_and_attributes(
            session
        )

        _validate_all_categories_in_config_exist(collector_config, api_categories_data)
        _validate_all_categories_are_in_config(collector_config, api_categories_data)

        # Save dataset to file
        with (OUTPUT_DIR / output_name).open("w") as f:
            writer = csv.DictWriter(f, fieldnames=InputDatasetItem.model_fields)
            writer.writeheader()
            for result in _generate_input_dataset_items(
                session,
                collector_config,
                target_size=target_size,
            ):
                writer.writerow(result.model_dump())


def _collect_categories_with_subcategories_and_attributes(
    session: OAuth2Session,
) -> list[tuple[CategoryDetail, list[tuple[ChildCategory, list[CategoryAttribute]]]]]:
    """Collect all categories with their subcategories and attributes."""
    result: list[
        tuple[CategoryDetail, list[tuple[ChildCategory, list[CategoryAttribute]]]]
    ] = []

    categories = list(iter_categories(session, SiteId.BRAZIL))

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


def _generate_input_dataset_items(
    session: OAuth2Session,
    collector_config: CollectorConfig,
    target_size: int,
) -> Iterator[InputDatasetItem]:
    """Build a dataset of products from configured categories and queries."""

    # Collect all queries from categories and extra queries
    all_queries: list[tuple[str, str]] = []  # (query, source_info)

    # Add queries from included categories
    for category in collector_config.categories.include:
        for query in category.queries:
            all_queries.append((query, f"Category: {category.name}"))

    # Add extra queries
    for query in collector_config.extra_queries:
        all_queries.append((query, "Extra query"))

    print(f"Total queries to process: {len(all_queries)}")

    # Calculate how many products to collect per query (roughly equal distribution)
    products_per_query = max(1, target_size // len(all_queries))
    remaining_products = target_size

    collected_count = 0
    total_failures_count = 0

    with Progress() as progress:
        main_task = progress.add_task(
            "Building dataset...",
            total=target_size,
        )

        for i, (query, source_info) in enumerate(all_queries):
            if collected_count >= target_size:
                break

            # Calculate how many items to collect from this query
            # For the last query, collect all remaining products
            if i == len(all_queries) - 1:
                target_from_query = remaining_products
            else:
                target_from_query = min(products_per_query, remaining_products)

            if target_from_query <= 0:
                continue

            progress.console.print(
                f"Collecting {target_from_query:,} products for query '{query}' ({source_info})"
            )

            # Collect products from this query using pagination
            query_collected = 0
            consecutive_failures = 0

            try:
                for response in search_products_paginated(
                    session,
                    SiteId.BRAZIL,
                    query=query,
                    limit=QUERY_SIZE_LIMIT,
                ):
                    for result in response.results:
                        if query_collected >= target_from_query:
                            break

                        # Check if we've had too many consecutive failures
                        if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                            progress.console.print(
                                f"Skipping query '{query}' due to {consecutive_failures} consecutive product fetch failures"
                            )
                            break

                        try:
                            product = get_product(session, result.id)

                            yield InputDatasetItem.from_search_result_and_product(
                                result,
                                product,
                            )

                            query_collected += 1
                            collected_count += 1
                            remaining_products -= 1
                            consecutive_failures = 0  # Reset on success
                            progress.update(main_task, advance=1)

                        except HTTPError as e:
                            if e.response.status_code == 404:
                                # Product not found, skip this item
                                consecutive_failures += 1
                                total_failures_count += 1
                                progress.console.print(
                                    f"Product {result.id} not found (404), skipping..."
                                )
                                continue
                            else:
                                # Re-raise other HTTP errors
                                raise

                    if (
                        query_collected >= target_from_query
                        or consecutive_failures >= MAX_CONSECUTIVE_FAILURES
                    ):
                        break

            except Exception as e:
                progress.console.print(f"Error collecting from query '{query}': {e}")
                # Continue with next query instead of raising
                continue

            progress.console.print(
                f"Collected {query_collected:,} products from query '{query}' ({source_info})"
            )

    print(f"Dataset built with {collected_count:,} products")
    print(f"Total failures: {total_failures_count:,}")


if __name__ == "__main__":
    app()
