"""Example script demonstrating the usage of an agent."""

from typing import Annotated

import dotenv
import typer
from asyncer import runnify
from rich import print

from hazmate.agent.agent import HazmatAgent
from hazmate.agent.predictions import HazmatPrediction
from hazmate.input_datasets.input_items import HazmatInputItem

app = typer.Typer()


@app.command()
@runnify
async def main(
    model_name: Annotated[
        str,
        typer.Option(
            "--model-name",
            "-m",
            help="Model name to use. For example, 'openai:gpt-4o-mini' or 'google-gla:gemini-2.5-flash-lite-preview-06-17'",
        ),
    ] = "openai:gpt-4o-mini",
) -> None:
    """Demonstrate the agent usage with both output types."""
    dotenv.load_dotenv()

    # Create a simple agent (in practice, you'd load from env/config)
    agent = HazmatAgent.from_model_and_mcp_servers(
        model_name=model_name,
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

    print("[bold blue]=== Input Item (X only) ===[/bold blue]")
    print(f"[cyan]ID:[/cyan] {sample_item.item_id}")
    print(f"[cyan]Name:[/cyan] {sample_item.name}")
    print(f"[cyan]Description:[/cyan] {sample_item.description}")
    print()

    # Option 1: Get just the prediction (Y only)
    print("[bold blue]=== Prediction Only (Y only) ===[/bold blue]")
    prediction: HazmatPrediction = await agent.predict_item(sample_item)
    print(f"[cyan]Item ID:[/cyan] {prediction.item_id}")
    print(f"[cyan]Is Hazmat:[/cyan] {prediction.is_hazmat}")
    print(f"[cyan]Traits:[/cyan] {[trait for trait in prediction.traits]}")
    print(f"[cyan]Reason:[/cyan] {prediction.reason}")
    print()

    # Option 2: Get combined input + prediction (X+Y)
    print(
        "[bold blue]=== Combined Input + Prediction (X+Y): Labeled Item ===[/bold blue]"
    )
    combined = await agent.classify_item(sample_item)
    print(f"[cyan]Item ID:[/cyan] {combined.item_id}")
    print(f"[cyan]Product Name:[/cyan] {combined.name}")
    print(f"[cyan]Is Hazmat:[/cyan] {combined.is_hazmat}")
    print(f"[cyan]Traits:[/cyan] {[trait for trait in combined.traits]}")
    print(f"[cyan]Reason:[/cyan] {combined.reason}")
    print()


if __name__ == "__main__":
    app()
