"""Main entry point for the hazmate builder package.

This script is used to build the hazmate dataset.
"""

import asyncio
import csv
import enum
import json
from collections import Counter
from collections.abc import AsyncIterator
from pathlib import Path
from pprint import pformat
from typing import Annotated, assert_never

import typer
from asyncer import runnify
from requests.exceptions import HTTPError
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table

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
from hazmate.builder.queries.product import Product, get_product
from hazmate.builder.queries.search import search_products_paginated
from hazmate.utils.async_itertools import ainterleave, ainterleave_queued, aislice
from hazmate.utils.oauth import OAuth2Session

QUERY_SIZE_LIMIT = 500
MAX_CONSECUTIVE_FAILURES = 10  # Avoid infinite loops if many products fail
OUTPUT_DIR = Path("data")

app = typer.Typer()


class Goal(enum.StrEnum):
    BALANCE = "balance"
    SPEED = "speed"


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
    goal: Annotated[
        Goal,
        typer.Option(
            "--goal",
            "-g",
            help="Goal for the dataset collection. Use 'balance' to collect a balanced amount of items from each query, or 'speed' to collect as many items as possible as fast as possible.",
        ),
    ] = Goal.BALANCE,
):
    auth_config = AuthConfig.from_dotenv(".env")
    collector_config = CollectorConfig.from_yaml(config_path)

    async with start_oauth_session(auth_config) as session:
        api_categories_data = (
            await _collect_categories_with_subcategories_and_attributes(session)
        )

        _validate_all_categories_in_config_exist(collector_config, api_categories_data)
        _validate_all_categories_are_in_config(collector_config, api_categories_data)

        # Collect items for statistics
        collected_items: list[InputDatasetItem] = []

        # Save dataset to file
        output_path = OUTPUT_DIR / output_name
        if output_path.suffix.lower() not in (".jsonl", ".csv"):
            raise ValueError(f"Invalid output file extension: {output_path.suffix}")

        with output_path.open("w") as f:
            # Determine file format based on suffix
            if output_path.suffix.lower() == ".jsonl":
                # JSONL format - one JSON object per line
                # Start progress tracking for main collection
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TimeElapsedColumn(),
                    TimeRemainingColumn(),
                ) as progress:
                    main_progress_task = progress.add_task(
                        "[green]Collecting items... (0 / {:,})[/green]".format(
                            target_size
                        ),
                        total=None,
                    )

                    async for item in _generate_input_dataset_items(
                        session,
                        collector_config,
                        target_size=target_size,
                        progress_tracker=progress,
                        main_progress_task=main_progress_task,
                        goal=goal,
                    ):
                        f.write(json.dumps(item.model_dump()) + "\n")
                        collected_items.append(item)
            else:
                # CSV format (default)
                writer = csv.DictWriter(f, fieldnames=InputDatasetItem.model_fields)
                writer.writeheader()

                # Start progress tracking for main collection
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TimeElapsedColumn(),
                    TimeRemainingColumn(),
                ) as progress:
                    main_progress_task = progress.add_task(
                        "[green]Collecting items... (0 / {:,})[/green]".format(
                            target_size
                        ),
                        total=None,
                    )

                    async for item in _generate_input_dataset_items(
                        session,
                        collector_config,
                        target_size=target_size,
                        progress_tracker=progress,
                        main_progress_task=main_progress_task,
                        goal=goal,
                    ):
                        writer.writerow(item.model_dump())
                        collected_items.append(item)

        # Calculate and display statistics
        _calculate_and_display_statistics(collected_items, output_name)


def _calculate_and_display_statistics(
    items: list[InputDatasetItem], output_filename: str
) -> None:
    """Calculate and display interesting statistics about the collected dataset."""
    console = Console()

    console.print(
        f"\n[bold green]📊 Dataset Statistics for {output_filename}[/bold green]"
    )
    console.print(f"Total items collected: [bold]{len(items):,}[/bold]\n")

    # 1. Count of each domain_id
    domain_counts = Counter(item.domain_id for item in items)

    table = Table(
        title="Domain Distribution", show_header=True, header_style="bold magenta"
    )
    table.add_column("Domain ID", style="cyan")
    table.add_column("Count", justify="right", style="green")
    table.add_column("Percentage", justify="right", style="yellow")

    for domain_id, count in domain_counts.most_common():
        percentage = (count / len(items)) * 100
        table.add_row(domain_id, f"{count:,}", f"{percentage:.1f}%")

    console.print(table)
    console.print()

    # 2. Items with description or short_description
    items_with_description = sum(
        1
        for item in items
        if (item.description and item.description.strip())
        or (item.short_description and item.short_description.strip())
    )

    console.print(f"[bold]Content Analysis:[/bold]")
    console.print(
        f"Items with description or short_description: [green]{items_with_description:,}[/green] ([yellow]{(items_with_description / len(items) * 100):.1f}%[/yellow])"
    )

    # 3. Items with only description
    items_with_only_description = sum(
        1
        for item in items
        if (item.description and item.description.strip())
        and not (item.short_description and item.short_description.strip())
    )

    # 4. Items with only short_description
    items_with_only_short_description = sum(
        1
        for item in items
        if (item.short_description and item.short_description.strip())
        and not (item.description and item.description.strip())
    )

    # 5. Items with both descriptions
    items_with_both_descriptions = sum(
        1
        for item in items
        if (item.description and item.description.strip())
        and (item.short_description and item.short_description.strip())
    )

    console.print(
        f"Items with only description: [cyan]{items_with_only_description:,}[/cyan] ([yellow]{(items_with_only_description / len(items) * 100):.1f}%[/yellow])"
    )
    console.print(
        f"Items with only short_description: [cyan]{items_with_only_short_description:,}[/cyan] ([yellow]{(items_with_only_short_description / len(items) * 100):.1f}%[/yellow])"
    )
    console.print(
        f"Items with both descriptions: [cyan]{items_with_both_descriptions:,}[/cyan] ([yellow]{(items_with_both_descriptions / len(items) * 100):.1f}%[/yellow])"
    )

    # 6. Items with keywords
    items_with_keywords = sum(
        1 for item in items if item.keywords and item.keywords.strip()
    )

    console.print(
        f"Items with keywords: [green]{items_with_keywords:,}[/green] ([yellow]{(items_with_keywords / len(items) * 100):.1f}%[/yellow])"
    )

    # 7. Items with permalink
    items_with_permalink = sum(1 for item in items if item.permalink)
    console.print(
        f"Items with permalink: [green]{items_with_permalink:,}[/green] ([yellow]{(items_with_permalink / len(items) * 100):.1f}%[/yellow])"
    )

    # 8. Attribute statistics
    total_attributes = sum(len(item.attributes) for item in items)
    items_with_attributes = sum(1 for item in items if item.attributes)
    avg_attributes_per_item = total_attributes / len(items) if items else 0

    console.print(f"\n[bold]Structured Data Analysis:[/bold]")
    console.print(
        f"Items with attributes: [green]{items_with_attributes:,}[/green] ([yellow]{(items_with_attributes / len(items) * 100):.1f}%[/yellow])"
    )
    console.print(
        f"Total attributes across all items: [cyan]{total_attributes:,}[/cyan]"
    )
    console.print(
        f"Average attributes per item: [cyan]{avg_attributes_per_item:.1f}[/cyan]"
    )

    # 9. Main features statistics
    total_main_features = sum(len(item.main_features) for item in items)
    items_with_main_features = sum(1 for item in items if item.main_features)
    avg_main_features_per_item = total_main_features / len(items) if items else 0

    console.print(
        f"Items with main features: [green]{items_with_main_features:,}[/green] ([yellow]{(items_with_main_features / len(items) * 100):.1f}%[/yellow])"
    )
    console.print(
        f"Total main features across all items: [cyan]{total_main_features:,}[/cyan]"
    )
    console.print(
        f"Average main features per item: [cyan]{avg_main_features_per_item:.1f}[/cyan]"
    )

    # 10. Family name analysis
    family_counts = Counter(item.family_name for item in items)
    top_families = family_counts.most_common(10)

    console.print(f"\n[bold]Top 10 Product Families:[/bold]")
    family_table = Table(show_header=True, header_style="bold magenta")
    family_table.add_column("Family Name", style="cyan")
    family_table.add_column("Count", justify="right", style="green")
    family_table.add_column("Percentage", justify="right", style="yellow")

    for family_name, count in top_families:
        percentage = (count / len(items)) * 100
        family_table.add_row(family_name, f"{count:,}", f"{percentage:.1f}%")

    console.print(family_table)

    # 11. Text content richness analysis
    items_with_any_text = sum(
        1
        for item in items
        if any(
            [
                item.description and item.description.strip(),
                item.short_description and item.short_description.strip(),
                item.keywords and item.keywords.strip(),
            ]
        )
    )

    # Calculate average text length for items that have text
    text_lengths = []
    for item in items:
        total_text = ""
        if item.description:
            total_text += item.description
        if item.short_description:
            total_text += " " + item.short_description
        if item.keywords:
            total_text += " " + item.keywords
        if total_text.strip():
            text_lengths.append(len(total_text.strip()))

    avg_text_length = sum(text_lengths) / len(text_lengths) if text_lengths else 0

    console.print(f"\n[bold]Text Content Summary:[/bold]")
    console.print(
        f"Items with any text content: [green]{items_with_any_text:,}[/green] ([yellow]{(items_with_any_text / len(items) * 100):.1f}%[/yellow])"
    )
    console.print(f"Average text length (chars): [cyan]{avg_text_length:.0f}[/cyan]")
    console.print(
        f"Text content completeness score: [bold green]{((items_with_any_text / len(items)) * 100):.1f}%[/bold green]"
    )


async def _collect_categories_with_subcategories_and_attributes(
    session: OAuth2Session,
) -> list[tuple[CategoryDetail, list[tuple[ChildCategory, list[CategoryAttribute]]]]]:
    """Collect all categories with their subcategories and attributes."""
    categories = await get_categories(session, SiteId.BRAZIL)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
    ) as progress:
        main_task = progress.add_task("Collecting categories...", total=len(categories))

        # Step 1: Get all category details in parallel
        async with asyncio.TaskGroup() as tg:
            category_tasks = [
                tg.create_task(get_category(session, category_ref.id))
                for category_ref in categories
            ]

        # Step 2: Process each category and get child attributes in parallel
        result: list[
            tuple[CategoryDetail, list[tuple[ChildCategory, list[CategoryAttribute]]]]
        ] = []

        for category_ref, category_task in zip(categories, category_tasks, strict=True):
            category = category_task.result()
            subcategories: list[tuple[ChildCategory, list[CategoryAttribute]]] = []

            if category.children_categories:
                child_task = progress.add_task(
                    f"[cyan]Collecting children of {category_ref.name}[/cyan]",
                    total=len(category.children_categories),
                )

                # Get all child category attributes in parallel
                async with asyncio.TaskGroup() as child_tg:
                    attribute_tasks = [
                        child_tg.create_task(
                            get_category_attributes(session, child_category.id)
                        )
                        for child_category in category.children_categories
                    ]

                # Combine children with their attributes
                for child_category, attribute_task in zip(
                    category.children_categories, attribute_tasks, strict=True
                ):
                    attributes = attribute_task.result()
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

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
    ) as progress:
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

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
    ) as progress:
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
    progress_tracker: Progress,
    main_progress_task: TaskID,
    goal: Goal,
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

    # Create async iterators for each query
    query_iterators = [_items_from_query(session, query=query) for query in all_queries]

    # Interleave results and take exactly target_size items
    if goal == Goal.BALANCE:
        interleaved = ainterleave(*query_iterators)
    elif goal == Goal.SPEED:
        interleaved = ainterleave_queued(*query_iterators)
    else:
        assert_never(goal)

    limited = aislice(interleaved, 0, target_size)

    count = 0
    async for item in limited:
        yield item
        count += 1

        # Update main progress with current count
        progress_tracker.update(
            main_progress_task,
            description=f"[green]Collecting items... ({count:,} / {target_size:,})[/green]",
        )

    print(f"Collection complete: {count:,} items")


async def _items_from_query(
    session: OAuth2Session,
    query: str,
) -> AsyncIterator[InputDatasetItem]:
    """Generate items from a single query - simple async iterator."""
    consecutive_failures = 0
    items_collected = 0

    # Process each result
    async for search_response in search_products_paginated(
        session,
        SiteId.BRAZIL,
        query=query,
        limit=QUERY_SIZE_LIMIT,
    ):
        async with asyncio.TaskGroup() as tg:
            get_product_tasks = [
                tg.create_task(_maybe_get_product(session, search_result.id))
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
                if product is None:
                    continue

                item = InputDatasetItem.from_search_result_and_product(
                    search_result,
                    product,
                )
                yield item
                items_collected += 1
                consecutive_failures = 0

            except HTTPError as e:
                print(f"HTTP error in query '{query}': {e}")
                consecutive_failures += 1
                continue

    print(f"Query '{query}' completed: {items_collected:,} items collected")


async def _maybe_get_product(
    session: OAuth2Session,
    product_id: str,
) -> Product | None:
    """Get a product from the API, but return None if it's not found."""
    try:
        return await get_product(session, product_id)
    except HTTPError as e:
        print(f"HTTP error in product '{product_id}': {e}")
        return None


if __name__ == "__main__":
    app()
