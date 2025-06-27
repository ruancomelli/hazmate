#!/usr/bin/env python3
"""
Evaluation script for testing agent accuracy on certainly hazmat items.

This script loads the hazmat attributes configuration, filters items from the
input dataset that have those attributes (which are certainly hazmat), runs
the agent on them, and calculates accuracy metrics.
"""

from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Annotated

import dotenv
import typer
import yaml
from asyncer import runnify
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from hazmate.agent.agent import HazmatAgent
from hazmate.builder.input_dataset import InputDatasetItem
from hazmate.evaluation.attribute_evaluation_config import AttributeEvaluationConfig

app = typer.Typer()


def load_hazmat_config(config_path: Path) -> AttributeEvaluationConfig:
    """Load hazmat attributes configuration from YAML file."""
    with config_path.open() as f:
        config_data = yaml.safe_load(f)
    return AttributeEvaluationConfig.model_validate(config_data)


def is_certainly_hazmat(
    item: InputDatasetItem, config: AttributeEvaluationConfig
) -> bool:
    """Check if an item is certainly hazmat based on its attributes."""
    for item_attr in item.attributes:
        for hazmat_attr in config.hazmat_attributes:
            if (
                item_attr.name == hazmat_attr.name
                and item_attr.value_name == hazmat_attr.value
            ):
                return True
    return False


def filter_hazmat_items(
    items: Iterable[InputDatasetItem], config: AttributeEvaluationConfig
) -> Iterator[InputDatasetItem]:
    """Filter items that are certainly hazmat based on their attributes."""
    return (item for item in items if is_certainly_hazmat(item, config))


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
        "false_negatives": false_negatives,
        "accuracy": accuracy,
        "accuracy_percentage": accuracy * 100,
    }

    return metrics


def print_detailed_results(results, items_dict: dict[str, InputDatasetItem]):
    """Print detailed results for each item."""
    print("\n" + "=" * 80)
    print("DETAILED RESULTS")
    print("=" * 80)

    for result in results:
        item = items_dict.get(result.item_id)
        if not item:
            continue

        status = "✅ CORRECT" if result.is_hazmat else "❌ INCORRECT (False Negative)"
        print(f"\n{status}")
        print(f"Item ID: {result.item_id}")
        print(f"Name: {item.name}")
        print(f"Agent Classification: {'HAZMAT' if result.is_hazmat else 'NOT HAZMAT'}")

        if result.traits:
            print(f"Identified Traits: {', '.join(result.traits)}")

        print(f"Agent Reason: {result.reason}")

        # Show the hazmat attributes that made this item certainly hazmat
        hazmat_attrs = []
        for attr in item.attributes:
            attr_text = f"{attr.name}: {attr.value_name}"
            hazmat_attrs.append(attr_text)

        if hazmat_attrs:
            print(f"Hazmat Attributes: {', '.join(hazmat_attrs)}")

        print("-" * 40)


@app.command()
@runnify
async def main(
    input: Annotated[
        Path,
        typer.Option(
            "--input",
            "-i",
            help="Path to the input dataset",
        ),
    ] = Path("data", "input_dataset.jsonl"),
    config: Annotated[
        Path,
        typer.Option(
            "--config",
            "-c",
            help="Path to the hazmat attributes configuration",
        ),
    ] = Path("hazmat-attributes-config.yaml"),
    batch_size: Annotated[
        int,
        typer.Option(
            "--batch-size",
            "-b",
            help="Batch size",
        ),
    ] = 10,
    model_name: Annotated[
        str,
        typer.Option(
            "--model-name",
            "-m",
            help="Model name. If you want to use an Ollama model, prefix the model name with 'ollama:', optionally appended with `@<port>`.",
        ),
    ] = "openai:gpt-4o-mini",
    max_items: Annotated[
        int,
        typer.Option(
            "--max-items",
            help="Maximum number of hazmat items to evaluate (0 for all)",
        ),
    ] = 0,
    detailed: Annotated[
        bool,
        typer.Option(
            "--detailed",
            help="Show detailed results for each item",
        ),
    ] = False,
):
    """Evaluate agent accuracy on certainly hazmat items."""

    print("🔬 Hazmat Agent Evaluation")
    print("=" * 50)

    # Load environment variables
    dotenv.load_dotenv()

    # Load hazmat configuration
    print(f"📋 Loading hazmat configuration from {config}")
    hazmat_config = load_hazmat_config(config)
    print(f"   Found {len(hazmat_config.hazmat_attributes)} hazmat attribute patterns")

    # Load input dataset
    print(f"📦 Loading input dataset from {input}")
    with input.open() as f:
        all_items = [InputDatasetItem.model_validate_json(line) for line in f]
    print(f"   Loaded {len(all_items)} total items")

    # Filter for certainly hazmat items
    print("🔍 Filtering for certainly hazmat items...")
    hazmat_items = list(filter_hazmat_items(all_items, hazmat_config))
    print(f"   Found {len(hazmat_items)} certainly hazmat items")

    if len(hazmat_items) == 0:
        print(
            "❌ No certainly hazmat items found! Check the configuration and dataset."
        )
        return

    # Limit items if requested
    if max_items > 0 and len(hazmat_items) > max_items:
        hazmat_items = hazmat_items[:max_items]
        print(f"   Limited to {max_items} items for evaluation")

    # Configure model
    model: Model | str
    if model_name.startswith("ollama:"):
        splits = model_name.split("@")
        model_name = splits[0].removeprefix("ollama:")
        port = splits[1] if len(splits) > 1 else 11434
        model = OpenAIModel(
            model_name=model_name,
            provider=OpenAIProvider(base_url=f"http://localhost:{port}/v1"),
        )
    else:
        model = model_name

    # Create agent
    print(f"🤖 Creating agent with model: {model}")
    agent = HazmatAgent.from_model_and_mcp_servers(
        model_name=model,
        mcp_servers=(),
    )

    # Process items in batches
    print(f"🔄 Processing {len(hazmat_items)} items in batches of {batch_size}")
    items_to_process = list(hazmat_items)
    all_results = []

    while items_to_process:
        remaining = len(items_to_process)
        print(f"   Items remaining: {remaining}")

        # Get batch
        batch_size_actual = min(batch_size, remaining)
        batch = [items_to_process.pop() for _ in range(batch_size_actual)]

        # Process batch
        try:
            results = await agent.classify_batch(batch, verify_ids=False)
            processed_ids = {result.item_id for result in results}
            print(f"   Processed {len(processed_ids)} items")

            # Re-add items that were not processed
            items_to_process.extend(
                item for item in batch if item.item_id not in processed_ids
            )
            all_results.extend(results)

        except Exception as e:
            print(f"   ❌ Error processing batch - trying again: {e}")
            # Add items back to process list
            items_to_process.extend(batch)

    # Print detailed results if requested
    print("\n" + "=" * 50)
    print("DETAILED RESULTS")
    print("=" * 50)
    if detailed and all_results:
        items_dict = {item.item_id: item for item in hazmat_items}
        print_detailed_results(all_results, items_dict)
    # Print hazmat attributes that were used for filtering
    print("\n📋 Hazmat attributes used for filtering:")
    for attr in hazmat_config.hazmat_attributes:
        print(f"   • {attr.name}: {attr.value} {attr.tags}")

    # Calculate metrics
    print("\n📊 Calculating accuracy metrics...")
    metrics = calculate_accuracy_metrics(all_results, len(hazmat_items))

    # Print summary
    print("\n" + "=" * 50)
    print("EVALUATION SUMMARY")
    print("=" * 50)
    print(f"Total items evaluated: {metrics['total_items']}")
    print(f"Expected hazmat items: {metrics['expected_hazmat']}")
    print(f"Correctly identified as hazmat: {metrics['correctly_identified_hazmat']}")
    print(f"False negatives (missed hazmat): {metrics['false_negatives']}")
    print(f"Accuracy: {metrics['accuracy_percentage']:.1f}%")


if __name__ == "__main__":
    app()
