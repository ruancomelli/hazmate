#!/usr/bin/env python3
"""
Filter script for extracting certainly hazmat items from input dataset.

This script loads the hazmat attributes configuration, filters items from the
input dataset that have those attributes (which are certainly hazmat), and
saves them to a new output dataset file.
"""

from pathlib import Path
from typing import Annotated

import typer
from loguru import logger
from rich import print

from hazmate.evaluation.attribute_evaluation_config import AttributeEvaluationConfig
from hazmate.input_datasets.input_items import HazmatInputItem

app = typer.Typer()


@app.command()
def main(
    input: Annotated[
        Path,
        typer.Option(
            "--input",
            "-i",
            help="Path to the input dataset. Example: data/input_dataset.jsonl",
        ),
    ],
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Path to the output filtered dataset. Example: data/hazmat_filtered_dataset.jsonl",
        ),
    ],
    config: Annotated[
        Path,
        typer.Option(
            "--config",
            "-c",
            help="Path to the hazmat attributes configuration",
        ),
    ] = Path("hazmat-attributes-config.yaml"),
):
    """Filter input dataset to contain only certainly hazmat items."""

    print("[bold green]🔍 Hazmat Items Filter[/bold green]")
    print("=" * 50)

    # Load hazmat configuration
    print(f"[blue]📋 Loading hazmat configuration from[/blue] {config}")
    hazmat_config = AttributeEvaluationConfig.from_yaml_file(config)
    print(
        f"   [green]Found {len(hazmat_config.hazmat_attributes)} hazmat attribute patterns[/green]"
    )

    # Load input dataset
    print(f"[blue]📦 Loading input dataset from[/blue] {input}")
    with input.open() as f:
        all_items = [HazmatInputItem.model_validate_json(line) for line in f]
    print(f"   [green]Loaded {len(all_items)} total items[/green]")

    # Filter for certainly hazmat items
    logger.info("Filtering for hazmat items...")
    hazmat_items = [item for item in all_items if hazmat_config.is_hazmat(item)]
    print(f"   [green]Found {len(hazmat_items)} hazmat items[/green]")

    if len(hazmat_items) == 0:
        print(
            "[red]❌ No hazmat items found! Check the configuration and dataset.[/red]"
        )
        return

    # Save filtered dataset
    print(f"[blue]💾 Saving filtered dataset to[/blue] {output}")
    output.parent.mkdir(parents=True, exist_ok=True)

    with output.open("w") as f:
        for item in hazmat_items:
            f.write(item.model_dump_json() + "\n")

    print(
        f"[bold green]✅ Successfully filtered {len(hazmat_items)} hazmat items[/bold green]"
    )

    # Print summary of hazmat attributes found
    print("\n[bold blue]📊 Summary of hazmat attributes found:[/bold blue]")
    attribute_counts: dict[str, int] = {}
    for item in hazmat_items:
        for item_attr in item.attributes:
            for hazmat_attr in hazmat_config.hazmat_attributes:
                if (
                    item_attr.name == hazmat_attr.name
                    and item_attr.value_name == hazmat_attr.value
                ):
                    attr_key = f"{hazmat_attr.name}: {hazmat_attr.value}"
                    attribute_counts[attr_key] = attribute_counts.get(attr_key, 0) + 1

    for attr, count in sorted(attribute_counts.items()):
        print(f"   [cyan]•[/cyan] {attr}: [green]{count} items[/green]")


if __name__ == "__main__":
    app()
