#!/usr/bin/env python3
"""
Split a labeled items dataset into hazmat and non-hazmat subsets.

This script loads a JSONL file containing HazmatLabeledItem objects and splits them
into two separate files based on the is_hazmat classification.

Expected workflow:
1. Use __main__.py to generate labeled predictions
2. Use this script to split the results by hazmat classification
"""

from pathlib import Path
from typing import Annotated

import typer
from loguru import logger
from rich import print

from hazmate.agent.labeled_items import HazmatLabeledItem

app = typer.Typer()


def load_labeled_items(input_file: Path) -> list[HazmatLabeledItem]:
    """Load labeled items from JSONL file."""
    labeled_items = []

    with input_file.open() as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            try:
                labeled_item = HazmatLabeledItem.model_validate_json(line)
                labeled_items.append(labeled_item)
            except Exception as e:
                logger.error(f"Error parsing line {line_num} in input file: {e}")
                logger.debug(f"Line: {line[:100]}...")
                continue

    return labeled_items


def write_labeled_items(items: list[HazmatLabeledItem], output_file: Path) -> None:
    """Write labeled items to JSONL file."""
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open("w") as f:
        for item in items:
            f.write(item.model_dump_json() + "\n")


@app.command()
def main(
    input: Annotated[
        Path,
        typer.Option(
            "--input",
            "-i",
            help="Path to the labeled items dataset (JSONL file with HazmatLabeledItem objects)",
        ),
    ],
    output_dir: Annotated[
        Path | None,
        typer.Option(
            "--output-dir",
            "-o",
            help="Directory to write the split datasets (defaults to same directory as input)",
        ),
    ] = None,
) -> None:
    """Split a labeled items dataset into hazmat and non-hazmat subsets.

    For example:
    ```bash
    python scripts/split_labeled_items_by_hazmat.py --input data/labeled_results.jsonl
    ```
    will create:
    ```
    data/labeled_results.hazmat.jsonl
    data/labeled_results.non_hazmat.jsonl
    ```
    """

    print(
        "[bold green]🔬 Splitting Labeled Items by Hazmat Classification[/bold green]"
    )
    print("=" * 60)

    # Set default output directory
    if output_dir is None:
        output_dir = input.parent

    # Load labeled items
    print(f"[blue]📋 Loading labeled items from[/blue] {input}")
    labeled_items = load_labeled_items(input)
    print(f"   [green]Loaded {len(labeled_items)} labeled items[/green]")

    if len(labeled_items) == 0:
        print("[red]❌ No labeled items found! Check the file.[/red]")
        return

    # Split by hazmat classification
    hazmat_items = [item for item in labeled_items if item.is_hazmat]
    non_hazmat_items = [item for item in labeled_items if not item.is_hazmat]

    print(f"[cyan]Items classified as hazmat:[/cyan] {len(hazmat_items)}")
    print(f"[cyan]Items classified as non-hazmat:[/cyan] {len(non_hazmat_items)}")

    # Generate output filenames
    base_name = input.stem
    hazmat_output = output_dir / f"{base_name}.hazmat.jsonl"
    non_hazmat_output = output_dir / f"{base_name}.non_hazmat.jsonl"

    # Write hazmat items
    if hazmat_items:
        print(
            f"[green]📝 Writing {len(hazmat_items)} hazmat items to[/green] {hazmat_output}"
        )
        write_labeled_items(hazmat_items, hazmat_output)
    else:
        print("[yellow]⚠️ No hazmat items to write[/yellow]")

    # Write non-hazmat items
    if non_hazmat_items:
        print(
            f"[green]📝 Writing {len(non_hazmat_items)} non-hazmat items to[/green] {non_hazmat_output}"
        )
        write_labeled_items(non_hazmat_items, non_hazmat_output)
    else:
        print("[yellow]⚠️ No non-hazmat items to write[/yellow]")

    # Summary
    print("\n" + "=" * 60)
    print("[bold blue]SPLIT SUMMARY[/bold blue]")
    print("=" * 60)
    print(f"[cyan]Total items processed:[/cyan] {len(labeled_items)}")
    print(
        f"[cyan]Hazmat items:[/cyan] {len(hazmat_items)} ({len(hazmat_items) / len(labeled_items) * 100:.1f}%)"
    )
    print(
        f"[cyan]Non-hazmat items:[/cyan] {len(non_hazmat_items)} ({len(non_hazmat_items) / len(labeled_items) * 100:.1f}%)"
    )

    if hazmat_items:
        print(f"[green]✅ Hazmat items saved to:[/green] {hazmat_output}")
    if non_hazmat_items:
        print(f"[green]✅ Non-hazmat items saved to:[/green] {non_hazmat_output}")


if __name__ == "__main__":
    app()
