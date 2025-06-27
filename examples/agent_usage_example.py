#!/usr/bin/env python3
"""Example script demonstrating the new agent structure.

This shows how to use:
1. HazmatPrediction - just the prediction results (Y only)
2. HazmatLabeledItem - combined input + prediction data (X+Y)
3. HazmatInputItem - just the input data (X only)
"""

import asyncio
from pathlib import Path

from hazmate.agent.agent import HazmatAgent
from hazmate.agent.labeled_items import HazmatLabeledItem
from hazmate.agent.predictions import HazmatPrediction
from hazmate.input_datasets.input_items import HazmatInputItem


async def main():
    """Demonstrate the agent usage with both output types."""

    # Create a simple agent (in practice, you'd load from env/config)
    agent = HazmatAgent.from_model_and_mcp_servers(
        model_name="openai:gpt-4o-mini",  # You'll need OpenAI API key
        mcp_servers=(),
    )

    # Create a sample input item (X - input only)
    sample_item = HazmatInputItem(
        item_id="MLU123456789",
        name="Acetone Nail Polish Remover 100ml",
        domain_id="MLA-BEAUTY",
        family_name="Nail Care",
        description="Professional grade acetone nail polish remover. Effectively removes all types of nail polish including gel and long-lasting formulas.",
        short_description="Acetone nail polish remover",
        keywords="acetone nail polish remover beauty manicure",
    )

    print("=== Input Item (X only) ===")
    print(f"ID: {sample_item.item_id}")
    print(f"Name: {sample_item.name}")
    print(f"Description: {sample_item.description}")
    print()

    # Option 1: Get just the prediction (Y only)
    print("=== Prediction Only (Y only) ===")
    prediction: HazmatPrediction = await agent.predict_item(sample_item)
    print(f"Item ID: {prediction.item_id}")
    print(f"Is Hazmat: {prediction.is_hazmat}")
    print(f"Traits: {[trait for trait in prediction.traits]}")
    print(f"Reason: {prediction.reason}")
    print()

    # Option 2: Get combined input + prediction (X+Y)
    print("=== Combined Input + Prediction (X+Y) ===")
    combined: HazmatLabeledItem = await agent.classify_item(sample_item)
    print(f"Item ID: {combined.item_id}")
    print(f"Product Name: {combined.name}")
    print(f"Is Hazmat: {combined.is_hazmat}")
    print(f"Traits: {[trait for trait in combined.traits]}")
    print(f"Reason: {combined.reason}")
    print()

    # Option 3: Create combined result manually
    print("=== Manual Combination (X+Y from X and Y) ===")
    manual_combined = HazmatLabeledItem.from_input_and_prediction(
        input_item=sample_item,
        prediction=prediction,
    )
    print(f"Manual combination matches automatic: {manual_combined == combined}")
    print()

    # Option 4: Export to CSV-friendly format
    print("=== CSV Export Format ===")
    csv_data = combined.to_flat_dict()
    for key, value in csv_data.items():
        print(f"{key}: {value}")

    print("\n=== Usage Summary ===")
    print("1. HazmatInputItem: Input data only (X)")
    print("2. HazmatPrediction: Prediction only (Y) - includes item_id for pairing")
    print("3. HazmatLabeledItem: Combined input + prediction (X+Y)")
    print("4. Use agent.predict_item() when you only need the prediction")
    print("5. Use agent.classify_item() when you need input + prediction together")
    print("6. Use HazmatLabeledItem.from_input_and_prediction() to combine manually")
    print("7. Use .to_flat_dict() to get CSV-friendly format")


if __name__ == "__main__":
    # Note: You'll need to set OPENAI_API_KEY environment variable
    import os

    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  Set OPENAI_API_KEY environment variable to run this example")
        print(
            "This is just a demonstration of the structure - you can still see the concepts!"
        )
    else:
        asyncio.run(main())
