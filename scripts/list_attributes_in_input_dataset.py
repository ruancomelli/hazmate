from collections import Counter, defaultdict
from pathlib import Path

import typer
from rich import print

from hazmate.input_datasets.input_items import HazmatInputItem

app = typer.Typer()


@app.command()
def list_attributes(input_dataset_path: Path):
    attributes: defaultdict[str, Counter[str]] = defaultdict(Counter)
    with open(input_dataset_path, "r") as f:
        for row in f:
            item = HazmatInputItem.model_validate_json(row)
            for attribute in item.attributes:
                attributes[attribute.name][attribute.value_name] += 1

    for name, value_names in sorted(attributes.items()):
        print(
            f"[bold blue]{name}:[/bold blue] {' | '.join(f'[cyan]{value_name}[/cyan] ([green]{count}[/green])' for value_name, count in value_names.most_common(10))}"
        )


if __name__ == "__main__":
    app()
