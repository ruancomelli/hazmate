#!/usr/bin/env python3
"""
Evaluation script for testing agent accuracy on certainly hazmat items.

This script loads ground-truth hazmat items and predictions from files,
matches them up, and calculates accuracy metrics. It does NOT run models.

Expected workflow:
1. Use filter_hazmat_items.py to create ground-truth hazmat items file
2. Use __main__.py to generate predictions on input dataset
3. Use this script to evaluate predictions against ground-truth
"""

from pathlib import Path
from typing import Annotated

import typer
from loguru import logger
from rich import print

from hazmate.agent.labeled_items import HazmatLabeledItem
from hazmate.agent.predictions import HazmatPrediction
from hazmate.input_datasets.input_items import HazmatInputItem

app = typer.Typer()


def calculate_accuracy_metrics(results, expected_hazmat_count: int):
    """Calculate accuracy metrics for the agent's results."""
    total_processed = len(results)
    correctly_identified_hazmat = sum(1 for result in results if result.is_hazmat)

    # Since all items should be hazmat, accuracy is the percentage correctly identified
    accuracy = (
        correctly_identified_hazmat / total_processed if total_processed > 0 else 0
    )

    # Detailed breakdown
    false_negatives = total_processed - correctly_identified_hazmat

    metrics = {
        "total_items": total_processed,
        "expected_hazmat": expected_hazmat_count,
        "correctly_identified_hazmat": correctly_identified_hazmat,
        "correctly_identified_hazmat_percentage": accuracy,
        "false_negatives": false_negatives,
        "false_negatives_percentage": false_negatives / total_processed,
        "accuracy": accuracy,
    }

    return metrics


def print_detailed_results(results, items_dict: dict[str, HazmatInputItem]):
    """Print detailed results for each item."""
    print("\n" + "=" * 80)
    print("[bold blue]DETAILED RESULTS[/bold blue]")
    print("=" * 80)

    for result in results:
        item = items_dict.get(result.item_id)
        if not item:
            continue

        status = (
            "[green]✅ CORRECT[/green]"
            if result.is_hazmat
            else "[red]❌ INCORRECT (False Negative)[/red]"
        )
        print(f"\n{status}")
        print(f"[cyan]Item ID:[/cyan] {result.item_id}")
        print(f"[cyan]Name:[/cyan] {item.name}")
        print(
            f"[cyan]Agent Classification:[/cyan] {'HAZMAT' if result.is_hazmat else 'NOT HAZMAT'}"
        )

        if result.traits:
            print(
                f"[cyan]Identified Traits:[/cyan] {', '.join(str(trait) for trait in result.traits)}"
            )

        print(f"[cyan]Agent Reason:[/cyan] {result.reason}")

        # Show the hazmat attributes that made this item certainly hazmat
        hazmat_attrs = []
        for attr in item.attributes:
            attr_text = f"{attr.name}: {attr.value_name}"
            hazmat_attrs.append(attr_text)

        if hazmat_attrs:
            print(f"[cyan]Hazmat Attributes:[/cyan] {', '.join(hazmat_attrs)}")

        print("-" * 40)


def load_predictions(predictions_file: Path) -> list[HazmatPrediction]:
    """Load predictions from file.

    The file can contain either HazmatPrediction or HazmatLabeledItem objects.
    If it contains HazmatLabeledItem, we extract the prediction part.
    """
    predictions = []

    with predictions_file.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                # Try loading as HazmatPrediction first
                prediction = HazmatPrediction.model_validate_json(line)
                predictions.append(prediction)
            except Exception:
                try:
                    # If that fails, try loading as HazmatLabeledItem and extract prediction
                    labeled_item = HazmatLabeledItem.model_validate_json(line)
                    prediction = labeled_item.prediction
                    predictions.append(prediction)
                except Exception as e:
                    logger.error(f"Error parsing line in predictions file: {e}")
                    logger.debug(f"Line: {line[:100]}...")
                    continue

    return predictions


@app.command()
def main(
    ground_truth: Annotated[
        Path,
        typer.Option(
            "--ground-truth",
            "-g",
            help="Path to the ground-truth hazmat items dataset (output of filter_hazmat_items.py)",
        ),
    ],
    predictions: Annotated[
        Path,
        typer.Option(
            "--predictions",
            "-p",
            help="Path to the predictions dataset (output of hazmate.agent:main).",
        ),
    ],
    detailed: Annotated[
        bool,
        typer.Option(
            "--detailed",
            help="Show detailed results for each item",
        ),
    ] = False,
):
    """Evaluate agent predictions against ground-truth hazmat items."""

    print(
        "[bold green]🔬 Hazmat Agent Evaluation (Pre-computed Predictions)[/bold green]"
    )
    print("=" * 50)

    # Load ground-truth hazmat items
    print(f"[blue]📋 Loading ground-truth hazmat items from[/blue] {ground_truth}")
    with ground_truth.open() as f:
        hazmat_items = [HazmatInputItem.model_validate_json(line) for line in f]
    print(f"   [green]Loaded {len(hazmat_items)} ground-truth hazmat items[/green]")

    if len(hazmat_items) == 0:
        print("[red]❌ No ground-truth hazmat items found! Check the file.[/red]")
        return

    # Load predictions
    print(f"[blue]📦 Loading predictions from[/blue] {predictions}")
    all_predictions = load_predictions(predictions)
    print(f"   [green]Loaded {len(all_predictions)} total predictions[/green]")

    # Create mapping of predictions by item_id
    predictions_by_id = {pred.item_id: pred for pred in all_predictions}

    # Find predictions for ground-truth items
    matched_predictions = []
    missing_predictions = []

    for item in hazmat_items:
        if item.item_id in predictions_by_id:
            matched_predictions.append(predictions_by_id[item.item_id])
        else:
            missing_predictions.append(item.item_id)

    print(
        f"   [green]Found predictions for {len(matched_predictions)} out of {len(hazmat_items)} ground-truth items[/green]"
    )

    if missing_predictions:
        logger.warning(f"Missing predictions for {len(missing_predictions)} items:")
        for item_id in missing_predictions[:10]:  # Show first 10
            logger.debug(f"  • {item_id}")
        if len(missing_predictions) > 10:
            logger.debug(f"  ... and {len(missing_predictions) - 10} more")

    if len(matched_predictions) == 0:
        print(
            "[red]❌ No matching predictions found! Check that the item IDs match between files.[/red]"
        )
        return

    # Print detailed results if requested
    if detailed and matched_predictions:
        items_dict = {item.item_id: item for item in hazmat_items}
        print_detailed_results(matched_predictions, items_dict)

    # Calculate metrics
    logger.info("Calculating accuracy metrics...")
    metrics = calculate_accuracy_metrics(matched_predictions, len(hazmat_items))

    # Print summary
    print("\n" + "=" * 50)
    print("[bold blue]EVALUATION SUMMARY[/bold blue]")
    print("=" * 50)
    print(f"[cyan]Ground-truth hazmat items:[/cyan] {len(hazmat_items)}")
    print(f"[cyan]Items with predictions:[/cyan] {metrics['total_items']}")
    print(f"[cyan]Items without predictions:[/cyan] {len(missing_predictions)}")
    print(
        f"[cyan]Correctly identified as hazmat:[/cyan] {metrics['correctly_identified_hazmat']} ({metrics['correctly_identified_hazmat_percentage']:.1%})"
    )
    print(
        f"[cyan]False negatives (missed hazmat):[/cyan] {metrics['false_negatives']} ({metrics['false_negatives_percentage']:.1%})"
    )
    print(f"[bold green]Accuracy:[/bold green] {metrics['accuracy']:.1%}")

    if missing_predictions:
        logger.warning(
            f"{len(missing_predictions)} items were missing predictions and excluded from accuracy calculation."
        )


if __name__ == "__main__":
    app()
