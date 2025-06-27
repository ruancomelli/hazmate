"""Example script demonstrating the usage of ExampleStore for RAG-based hazmat classification."""

import dotenv
import typer
from rich import print
from rich.console import Console
from rich.table import Table

from hazmate.agent.example_store import ExampleStore
from hazmate.agent.hazmat_traits import KnownHazmatTrait
from hazmate.agent.labeled_items import HazmatLabeledItem
from hazmate.input_datasets.input_items import HazmatInputItem

app = typer.Typer()
console = Console()


def create_sample_labeled_examples() -> list[HazmatLabeledItem]:
    """Create sample labeled examples for demonstration."""
    return [
        # Hazmat example 1: Flammable liquid
        HazmatLabeledItem(
            item_id="MLU001",
            name="Acetone Nail Polish Remover 500ml",
            domain_id="MLA-BEAUTY",
            family_name="Nail Care",
            description="Professional grade acetone nail polish remover. Contains 99% pure acetone. Highly flammable liquid.",
            short_description="Acetone nail polish remover",
            keywords="acetone nail polish remover beauty flammable",
            is_hazmat=True,
            traits=[KnownHazmatTrait.FLAMMABLE, KnownHazmatTrait.TOXIC],
            reason="Contains acetone which is a highly flammable liquid (Class 3) and can cause respiratory irritation and skin/eye damage.",
        ),
        # Hazmat example 2: Corrosive
        HazmatLabeledItem(
            item_id="MLU002",
            name="Hydrochloric Acid Pool Cleaner 1L",
            domain_id="MLA-POOL",
            family_name="Pool Chemicals",
            description="Professional pool cleaning solution containing 20% hydrochloric acid. Removes calcium deposits and algae.",
            short_description="HCl pool cleaner",
            keywords="hydrochloric acid pool cleaner chemical corrosive",
            is_hazmat=True,
            traits=[KnownHazmatTrait.CORROSIVE, KnownHazmatTrait.TOXIC],
            reason="Contains hydrochloric acid which is highly corrosive (Class 8) and can cause severe burns to skin, eyes, and respiratory system.",
        ),
        # Non-hazmat example 1: Regular cosmetics
        HazmatLabeledItem(
            item_id="MLU003",
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
        # Hazmat example 3: Pressurized container
        HazmatLabeledItem(
            item_id="MLU004",
            name="Spray Paint Red Matte 400ml",
            domain_id="MLA-TOOLS",
            family_name="Paints",
            description="High-quality acrylic spray paint in pressurized aerosol can. Contains flammable propellants.",
            short_description="Aerosol spray paint",
            keywords="spray paint aerosol pressurized flammable art",
            is_hazmat=True,
            traits=[KnownHazmatTrait.FLAMMABLE, KnownHazmatTrait.COMPRESSED_GAS],
            reason="Pressurized aerosol container (Class 2.1) with flammable propellants and solvents.",
        ),
        # Non-hazmat example 2: Electronics
        HazmatLabeledItem(
            item_id="MLU005",
            name="USB-C Cable 2m Fast Charging",
            domain_id="MLA-ELECTRONICS",
            family_name="Cables",
            description="High-quality USB-C to USB-A cable for fast charging and data transfer. Durable braided design.",
            short_description="USB-C charging cable",
            keywords="usb cable charging electronics fast",
            is_hazmat=False,
            traits=[],
            reason="Electronic cable with no hazardous materials. Standard shipping applies.",
        ),
    ]


def create_sample_input_item() -> HazmatInputItem:
    """Create a sample input item for testing retrieval."""
    return HazmatInputItem(
        item_id="MLU999",
        name="Industrial Solvent Cleaner 1L",
        domain_id="MLA-INDUSTRIAL",
        family_name="Cleaning Supplies",
        description="Heavy-duty industrial solvent for degreasing machinery. Contains organic solvents and petroleum distillates.",
        short_description="Industrial solvent cleaner",
        keywords="solvent cleaner industrial degreasing chemical",
    )


@app.command()
def demo_basic_usage() -> None:
    """Demonstrate basic ExampleStore usage: adding examples and retrieving stats."""
    print("[bold blue]=== ExampleStore Basic Usage Demo ===[/bold blue]")

    # Create store with custom config
    store = ExampleStore.from_embedding_model_name_and_persist_directory(
        embedding_model_name="models/gemini-embedding-exp-03-07",
        persist_directory="examples/data/demo_examples",
    )

    # Clear any existing data for clean demo
    store.clear()

    print("[cyan]📊 Initial stats:[/cyan]")
    stats = store.get_stats()
    print(f"  Total examples: {stats['total_examples']}")
    print(f"  Hazmat examples: {stats['hazmat_examples']}")
    print(f"  Non-hazmat examples: {stats['non_hazmat_examples']}")
    print()

    # Add sample examples
    print("[cyan]📝 Adding sample labeled examples...[/cyan]")
    examples = create_sample_labeled_examples()

    # Add examples one by one (demonstrating single add)
    for i, example in enumerate(examples[:2]):
        store.add(example)
        print(f"  ✅ Added example {i + 1}: {example.name}")

    # Add remaining examples in batch (demonstrating batch add)
    store.add_batch(examples[2:])
    print(f"  ✅ Batch added {len(examples[2:])} more examples")
    print()

    # Show updated stats
    print("[cyan]📊 Updated stats:[/cyan]")
    stats = store.get_stats()
    print(f"  Total examples: {stats['total_examples']}")
    print(f"  Hazmat examples: {stats['hazmat_examples']}")
    print(f"  Non-hazmat examples: {stats['non_hazmat_examples']}")
    print()


@app.command()
def demo_retrieval() -> None:
    """Demonstrate example retrieval and RAG functionality."""
    print("[bold blue]=== ExampleStore Retrieval Demo ===[/bold blue]")

    # Ensure we have examples from the basic demo
    demo_basic_usage()

    store = ExampleStore.from_embedding_model_name_and_persist_directory(
        embedding_model_name="models/gemini-embedding-exp-03-07",
        persist_directory="examples/data/demo_examples",
    )

    # Create a sample input item for classification
    input_item = create_sample_input_item()

    print("[cyan]🔍 Input item to classify:[/cyan]")
    print(f"  ID: {input_item.item_id}")
    print(f"  Name: {input_item.name}")
    print(f"  Description: {input_item.description}")
    print()

    # Retrieve relevant examples
    print("[cyan]📚 Retrieving relevant examples...[/cyan]")
    similar_examples = store.retrieve(input_item, count=3)

    if similar_examples:
        # Create a nice table to display results
        table = Table(title="Similar Examples Found")
        table.add_column("Item ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column(
            "Is Hazmat",
            style="red" if any(ex.is_hazmat for ex in similar_examples) else "blue",
        )
        table.add_column("Traits", style="yellow")
        table.add_column("Reason", style="white", max_width=40)

        for example in similar_examples:
            traits_text = (
                ", ".join(
                    [
                        trait.value
                        if isinstance(trait, KnownHazmatTrait)
                        else trait.trait
                        for trait in example.traits
                    ]
                )
                if example.traits
                else "None"
            )

            table.add_row(
                example.item_id,
                example.name[:30] + "..." if len(example.name) > 30 else example.name,
                "✅ Yes" if example.is_hazmat else "❌ No",
                traits_text,
                example.reason[:60] + "..."
                if len(example.reason) > 60
                else example.reason,
            )

        console.print(table)
    else:
        print("  ❌ No similar examples found")

    print()


if __name__ == "__main__":
    dotenv.load_dotenv()
    app()
