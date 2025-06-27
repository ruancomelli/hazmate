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

    print("🔍 Hazmat Items Filter")
    print("=" * 50)

    # Load hazmat configuration
    print(f"📋 Loading hazmat configuration from {config}")
    hazmat_config = AttributeEvaluationConfig.from_yaml_file(config)
    print(f"   Found {len(hazmat_config.hazmat_attributes)} hazmat attribute patterns")

    # Load input dataset
    print(f"📦 Loading input dataset from {input}")
    with input.open() as f:
        all_items = [HazmatInputItem.model_validate_json(line) for line in f]
    print(f"   Loaded {len(all_items)} total items")

    # Filter for certainly hazmat items
    print("🔍 Filtering for hazmat items...")
    hazmat_items = [item for item in all_items if hazmat_config.is_hazmat(item)]
    print(f"   Found {len(hazmat_items)} hazmat items")

    if len(hazmat_items) == 0:
        print("❌ No hazmat items found! Check the configuration and dataset.")
        return

    # Save filtered dataset
    print(f"💾 Saving filtered dataset to {output}")
    output.parent.mkdir(parents=True, exist_ok=True)

    with output.open("w") as f:
        for item in hazmat_items:
            f.write(item.model_dump_json() + "\n")

    print(f"✅ Successfully filtered {len(hazmat_items)} hazmat items")

    # Print summary of hazmat attributes found
    print("\n📊 Summary of hazmat attributes found:")
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
        print(f"   • {attr}: {count} items")


if __name__ == "__main__":
    app()
