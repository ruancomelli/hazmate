import itertools
from pathlib import Path
from typing import Annotated

import typer
from rich import print

app = typer.Typer()


@app.command()
def main(
    input: Annotated[
        Path,
        typer.Option(
            "--input",
            "-i",
            help="Path to the dataset to split",
        ),
    ],
    count: Annotated[
        int,
        typer.Option(
            "--count",
            "-c",
            help="Number of subsets to split the dataset into",
        ),
    ],
) -> None:
    """Split a dataset into a given number of subsets.

    For example,
    ```bash
    python scripts/split_jsonl.py --input data/input_dataset.jsonl --count 10
    ```
    will create the following 10 subsets:
    ```
    data/input_dataset.10.0.jsonl
    data/input_dataset.10.1.jsonl
    ...
    data/input_dataset.10.9.jsonl
    ```
    (each subset is named `<input_file_name>.<count>.<index>.jsonl`)

    Note that this script accepts any `.jsonl` file as input, not only "input dataset" files.
    """
    items = input.read_text().splitlines()
    print(f"[blue]Splitting {len(items)} items into {count} subsets[/blue]")
    for i, lines in enumerate(itertools.batched(items, len(items) // count)):
        output = input.parent / f"{input.stem}.{count}.{i}.jsonl"
        print(f"[green]Writing subset {i} to[/green] {output}")
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w") as f:
            for line in lines:
                f.write(line + "\n")


if __name__ == "__main__":
    app()
