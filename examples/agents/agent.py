"""Example script demonstrating the usage of an agent with and without RAG."""

from typing import Annotated

import dotenv
import typer
from asyncer import runnify
from rich import print
from rich.console import Console
from rich.table import Table

from hazmate.agent.agent import HazmatAgent
from hazmate.agent.example_store import ExampleStore
from hazmate.agent.hazmat_traits import KnownHazmatTrait
from hazmate.agent.labeled_items import HazmatLabeledItem
from hazmate.agent.predictions import HazmatPrediction
from hazmate.input_datasets.input_items import HazmatInputItem

app = typer.Typer()
console = Console()


def create_sample_labeled_examples() -> list[HazmatLabeledItem]:
    """Create sample labeled examples for the knowledge base."""
    return [
        HazmatLabeledItem(
            item_id="KB001",
            name="Acetone Nail Polish Remover 500ml",
            domain_id="MLA-BEAUTY",
            family_name="Nail Care",
            description="Professional grade acetone nail polish remover. Contains 99% pure acetone.",
            short_description="Acetone nail polish remover",
            keywords="acetone nail polish remover beauty flammable",
            is_hazmat=True,
            traits=[KnownHazmatTrait.FLAMMABLE, KnownHazmatTrait.TOXIC],
            reason="Contains acetone which is a highly flammable liquid (Class 3) and can cause respiratory irritation.",
        ),
        HazmatLabeledItem(
            item_id="KB002",
            name="Natural Organic Shampoo 300ml",
            domain_id="MLA-BEAUTY",
            family_name="Hair Care",
            description="Gentle organic shampoo with natural ingredients. No sulfates, parabens or harsh chemicals.",
            short_description="Organic shampoo",
            keywords="organic shampoo natural hair care gentle",
            is_hazmat=False,
            traits=[],
            reason="Contains only natural organic ingredients with no hazardous chemicals. Safe for regular shipping.",
        ),
        HazmatLabeledItem(
            item_id="KB003",
            name="Propane Gas Cartridge 230g",
            domain_id="MLA-OUTDOOR",
            family_name="Camping Gas",
            description="High-pressure propane gas cartridge for camping stoves and portable heaters.",
            short_description="Propane gas cartridge",
            keywords="propane gas cartridge camping pressurized",
            is_hazmat=True,
            traits=[KnownHazmatTrait.FLAMMABLE, KnownHazmatTrait.COMPRESSED_GAS],
            reason="Pressurized flammable gas container (Class 2.1). Contains highly flammable propane under pressure.",
        ),
    ]


@app.command()
@runnify
async def basic_usage(
    model_name: Annotated[
        str,
        typer.Option(
            "--model-name",
            "-m",
            help="Model name to use. For example, 'openai:gpt-4o-mini' or 'google-gla:gemini-2.5-flash-lite-preview-06-17'",
        ),
    ] = "openai:gpt-4o-mini",
) -> None:
    """Demonstrate basic agent usage without RAG."""
    dotenv.load_dotenv()

    print("[bold blue]=== Basic Agent Usage (No RAG) ===[/bold blue]")

    # Create a basic agent (no RAG)
    agent = HazmatAgent.from_model(model_name)

    # Create a sample input item
    sample_item = HazmatInputItem(
        item_id="MLU123456789",
        name="Paint Thinner Solvent 1L",
        domain_id="MLA-TOOLS",
        family_name="Paint Supplies",
        description="High-quality paint thinner containing petroleum distillates. Used for thinning oil-based paints and cleaning brushes.",
        short_description="Paint thinner solvent",
        keywords="paint thinner solvent petroleum cleaning",
    )

    print(f"[cyan]Input Item:[/cyan] {sample_item.name}")
    print(f"[cyan]Description:[/cyan] {sample_item.description}")
    print()

    # Get prediction
    print("[cyan]🤖 Basic Agent Prediction:[/cyan]")
    prediction: HazmatPrediction = await agent.predict_item(sample_item)

    table = Table(title="Basic Agent Result")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Item ID", prediction.item_id)
    table.add_row("Is Hazmat", "✅ Yes" if prediction.is_hazmat else "❌ No")
    table.add_row("Traits", ", ".join(str(trait) for trait in prediction.traits))
    table.add_row("Reason", prediction.reason)

    console.print(table)


@app.command()
@runnify
async def rag_usage(
    model_name: Annotated[
        str,
        typer.Option(
            "--model-name",
            "-m",
            help="Model name to use",
        ),
    ] = "openai:gpt-4o-mini",
) -> None:
    """Demonstrate RAG-enhanced agent usage."""
    dotenv.load_dotenv()

    print("[bold blue]=== RAG-Enhanced Agent Usage ===[/bold blue]")

    # Setup example store with sample data
    print("[cyan]🔧 Setting up example store...[/cyan]")
    example_store = ExampleStore.from_embedding_model_name_and_persist_directory(
        persist_directory="examples/data/agent_demo_examples"
    )

    # Clear and populate with sample examples
    example_store.clear()
    sample_examples = create_sample_labeled_examples()
    example_store.add_batch(sample_examples)

    stats = example_store.get_stats()
    print(f"  ✅ Added {stats['total_examples']} examples to knowledge base")
    print()

    # Create RAG-enhanced agent
    agent = HazmatAgent.from_model(model_name, example_store=example_store)

    # Test item similar to knowledge base
    test_item = HazmatInputItem(
        item_id="TEST123",
        name="Isopropyl Alcohol Hand Sanitizer 250ml",
        domain_id="MLA-HEALTH",
        family_name="Hand Care",
        description="70% isopropyl alcohol-based hand sanitizer. Highly effective against germs and bacteria.",
        short_description="Alcohol hand sanitizer",
        keywords="isopropyl alcohol sanitizer flammable antiseptic",
    )

    print(f"[cyan]Test Item:[/cyan] {test_item.name}")
    print(f"[cyan]Description:[/cyan] {test_item.description}")
    print()

    # Get RAG-enhanced prediction
    print("[cyan]🧠 RAG-Enhanced Agent Prediction:[/cyan]")
    prediction = await agent.predict_item(test_item)

    table = Table(title="RAG-Enhanced Agent Result")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Item ID", prediction.item_id)
    table.add_row("Is Hazmat", "✅ Yes" if prediction.is_hazmat else "❌ No")
    table.add_row("Traits", ", ".join(str(trait) for trait in prediction.traits))
    table.add_row("Reason", prediction.reason)

    console.print(table)


@app.command()
@runnify
async def compare_agents(
    model_name: Annotated[
        str,
        typer.Option(
            "--model-name",
            "-m",
            help="Model name to use",
        ),
    ] = "openai:gpt-4o-mini",
) -> None:
    """Compare basic vs RAG-enhanced agent predictions."""
    dotenv.load_dotenv()

    print("[bold blue]=== Agent Comparison: Basic vs RAG-Enhanced ===[/bold blue]")

    # Setup example store
    example_store = ExampleStore.from_embedding_model_name_and_persist_directory(
        persist_directory="examples/data/agent_comparison_examples"
    )
    example_store.clear()
    example_store.add_batch(create_sample_labeled_examples())

    # Create both agents
    basic_agent = HazmatAgent.from_model(model_name)
    rag_agent = HazmatAgent.from_model(model_name, example_store=example_store)

    # Test item
    test_item = HazmatInputItem(
        item_id="COMPARE001",
        name="Butane Lighter Fuel Refill 300ml",
        domain_id="MLA-TOOLS",
        family_name="Lighters",
        description="High-purity butane fuel for refilling cigarette lighters and small torches. Pressurized aerosol container.",
        short_description="Butane lighter fuel",
        keywords="butane fuel lighter refill pressurized aerosol",
    )

    print(f"[cyan]🧪 Test Item:[/cyan] {test_item.name}")
    print(f"[cyan]Description:[/cyan] {test_item.description}")
    print()

    # Get predictions from both agents
    print("[cyan]🤖 Basic Agent:[/cyan]")
    basic_result = await basic_agent.predict_item(test_item)
    basic_table = Table(title="Basic Agent")
    basic_table.add_column("Property", style="cyan")
    basic_table.add_column("Value", style="blue")
    basic_table.add_row(
        "Classification", "HAZMAT" if basic_result.is_hazmat else "NOT HAZMAT"
    )
    basic_table.add_row(
        "Traits", ", ".join(str(trait) for trait in basic_result.traits)
    )
    basic_table.add_row(
        "Reason",
        basic_result.reason[:100] + "..."
        if len(basic_result.reason) > 100
        else basic_result.reason,
    )
    console.print(basic_table)
    print()

    print("[cyan]🧠 RAG-Enhanced Agent:[/cyan]")
    rag_result = await rag_agent.predict_item(test_item)
    rag_table = Table(title="RAG-Enhanced Agent")
    rag_table.add_column("Property", style="cyan")
    rag_table.add_column("Value", style="green")
    rag_table.add_row(
        "Classification", "HAZMAT" if rag_result.is_hazmat else "NOT HAZMAT"
    )
    rag_table.add_row("Traits", ", ".join(str(trait) for trait in rag_result.traits))
    rag_table.add_row(
        "Reason",
        rag_result.reason[:100] + "..."
        if len(rag_result.reason) > 100
        else rag_result.reason,
    )
    console.print(rag_table)
    print()

    # Show agreement
    agreement = basic_result.is_hazmat == rag_result.is_hazmat
    print(f"[cyan]🎯 Agent Agreement:[/cyan] {'✅ Yes' if agreement else '❌ No'}")


if __name__ == "__main__":
    app()
