"""Main entry point for the hazmate builder package.

This script is used to build the hazmate dataset.
"""

import asyncio
import csv
from collections.abc import AsyncIterator
from pathlib import Path
from pprint import pformat
from typing import Annotated

import typer
from asyncer import runnify
from requests.exceptions import HTTPError
from rich.progress import Progress, TaskID

from hazmate.builder.auth import start_oauth_session
from hazmate.builder.auth_config import AuthConfig
from hazmate.builder.collector_config import CollectorConfig
from hazmate.builder.input_dataset import InputDatasetItem
from hazmate.builder.queries.base import SiteId
from hazmate.builder.queries.categories import get_categories
from hazmate.builder.queries.category import CategoryDetail, ChildCategory, get_category
from hazmate.builder.queries.category_attributes import (
    CategoryAttribute,
    get_category_attributes,
)
from hazmate.builder.queries.product import get_product
from hazmate.builder.queries.search import search_products_paginated
from hazmate.utils.async_itertools import ainterleave_queued, aislice
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

    async with start_oauth_session(auth_config) as session:
        api_categories_data = (
            await _collect_categories_with_subcategories_and_attributes(session)
        )

        _validate_all_categories_in_config_exist(collector_config, api_categories_data)
        _validate_all_categories_are_in_config(collector_config, api_categories_data)

        # Save dataset to file
        with (OUTPUT_DIR / output_name).open("w") as f:
            writer = csv.DictWriter(f, fieldnames=InputDatasetItem.model_fields)
            writer.writeheader()

            # Start progress tracking for main collection
            with Progress() as progress:
                main_task = progress.add_task(
                    "[green]Collecting items...", total=target_size
                )

                async for item in _generate_input_dataset_items(
                    session,
                    collector_config,
                    target_size=target_size,
                    progress_tracker=progress,
                    main_progress_task=main_task,
                ):
                    writer.writerow(item.model_dump())


async def _collect_categories_with_subcategories_and_attributes(
    session: OAuth2Session,
) -> list[tuple[CategoryDetail, list[tuple[ChildCategory, list[CategoryAttribute]]]]]:
    """Collect all categories with their subcategories and attributes."""
    result: list[
        tuple[CategoryDetail, list[tuple[ChildCategory, list[CategoryAttribute]]]]
    ] = []

    categories = await get_categories(session, SiteId.BRAZIL)

    with Progress() as progress:
        main_task = progress.add_task("Collecting categories...", total=len(categories))

        for category_ref in categories:
            category = await get_category(session, category_ref.id)

            subcategories: list[tuple[ChildCategory, list[CategoryAttribute]]] = []

            if category.children_categories:
                child_task = progress.add_task(
                    f"[cyan]Collecting children of {category_ref.name}[/cyan]",
                    total=len(category.children_categories),
                )

                for child_category in category.children_categories:
                    attributes = await get_category_attributes(
                        session, child_category.id
                    )
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


async def _generate_input_dataset_items(
    session: OAuth2Session,
    collector_config: CollectorConfig,
    target_size: int,
    progress_tracker: Progress | None = None,
    main_progress_task: TaskID | None = None,
) -> AsyncIterator[InputDatasetItem]:
    """Build a dataset of products from configured categories and queries - elegant async version."""

    # Collect all queries
    all_queries = [
        query
        for category in collector_config.categories.include
        for query in category.queries
    ] + list(collector_config.extra_queries)

    print(f"Starting parallel collection from {len(all_queries)} queries")
    print(f"Target size: {target_size:,}")

    # Initialize query progress tasks if progress is available
    query_progress_tasks: dict[str, TaskID] = {}
    if progress_tracker:
        for query in all_queries:
            task_id = progress_tracker.add_task(
                f"[cyan]Query: {query[:50]}{'...' if len(query) > 50 else ''}[/cyan]",
                total=None,  # Unknown total for each query
                visible=False,  # Start hidden to avoid clutter
            )
            query_progress_tasks[query] = task_id

    # Create async iterators for each query
    query_iterators = [
        _items_from_query(
            session,
            query=query,
            progress_tracker=progress_tracker,
            query_progress_task=query_progress_tasks.get(query),
        )
        for query in all_queries
    ]

    # Interleave results and take exactly target_size items
    interleaved = ainterleave_queued(*query_iterators)
    limited = aislice(interleaved, 0, target_size)

    count = 0
    async for item in limited:
        yield item
        count += 1

        # Update main progress
        if progress_tracker and main_progress_task:
            progress_tracker.update(main_progress_task, advance=1)

        if count % 100 == 0:
            print(f"Collected {count:,} items so far...")

    print(f"Collection complete: {count:,} items")


async def _items_from_query(
    session: OAuth2Session,
    query: str,
    progress_tracker: Progress | None = None,
    query_progress_task: TaskID | None = None,
) -> AsyncIterator[InputDatasetItem]:
    """Generate items from a single query - simple async iterator."""

    print(f"Starting query: '{query}'")

    consecutive_failures = 0
    items_collected = 0

    # Make the query task visible once we start processing
    if progress_tracker and query_progress_task:
        progress_tracker.update(query_progress_task, visible=True)

    # Process each result
    async for search_response in search_products_paginated(
        session,
        SiteId.BRAZIL,
        query=query,
        limit=QUERY_SIZE_LIMIT,
    ):
        async with asyncio.TaskGroup() as tg:
            get_product_tasks = [
                tg.create_task(get_product(session, search_result.id))
                for search_result in search_response.results
            ]

        for search_result, product_task in zip(
            search_response.results,
            get_product_tasks,
            strict=True,
        ):
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                raise ValueError(
                    f"Query '{query}': stopping due to {consecutive_failures} consecutive failures"
                )

            try:
                product = product_task.result()
                item = InputDatasetItem.from_search_result_and_product(
                    search_result,
                    product,
                )
                yield item
                items_collected += 1
                consecutive_failures = 0

                # Update query-specific progress
                if progress_tracker and query_progress_task:
                    progress_tracker.update(
                        query_progress_task,
                        advance=1,
                        description=f"[cyan]Query: {query[:50]}{'...' if len(query) > 50 else ''} ({items_collected} items)[/cyan]",
                    )

            except HTTPError as e:
                print(f"HTTP error in query '{query}': {e}")
                consecutive_failures += 1
                continue

    # Remove completed query task to keep progress display clean
    if progress_tracker and query_progress_task:
        progress_tracker.remove_task(query_progress_task)

    print(f"Query '{query}' completed: {items_collected:,} items collected")


if __name__ == "__main__":
    app()
