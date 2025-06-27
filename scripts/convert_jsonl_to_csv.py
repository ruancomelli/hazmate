import csv
import itertools
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import typer
from rich import print

app = typer.Typer()


def convert_jsonl_to_csv(jsonl_path: Path, csv_path: Path):
    print(f"[blue]Converting[/blue] {jsonl_path} [blue]to[/blue] {csv_path}")
    with open(jsonl_path, "r") as f:
        write_csv(csv_path, (json.loads(line) for line in f))
    print(f"[green]✅ Conversion complete[/green]")


def write_csv(csv_path: Path, data: Iterable[dict[str, Any]]):
    """Write data to a CSV file.

    Detect the fieldnames from the first row of the data.
    """
    data_iter = iter(data)
    first_row = next(data_iter)
    fieldnames = list(first_row.keys())
    data_iter = itertools.chain([first_row], data_iter)
    with open(csv_path, "w") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data_iter)


if __name__ == "__main__":
    typer.run(convert_jsonl_to_csv)
