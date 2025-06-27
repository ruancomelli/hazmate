import asyncio
from collections.abc import Callable
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import dotenv
import typer
from asyncer import runnify
from loguru import logger
from rich import print

from hazmate.agent.agent import HazmatAgent
from hazmate.agent.example_store import ExampleStore
from hazmate.agent.labeled_items import HazmatLabeledItem
from hazmate.agent.predictions import HazmatPrediction
from hazmate.input_datasets.input_items import HazmatInputItem
from hazmate.utils.tokens import estimate_token_count

app = typer.Typer()


class OnExistingOutput(StrEnum):
    CONTINUE = "continue"
    OVERWRITE = "overwrite"
    RAISE = "raise"


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
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Path to the output dataset",
        ),
    ] = Path("data", "output_dataset.jsonl"),
    on_existing_output: Annotated[
        OnExistingOutput,
        typer.Option(
            "--on-existing-output",
            help=(
                "What to do if the output file already exists. "
                "'continue' will load existing results and only process remaining items. "
                "'overwrite' will start fresh and overwrite the existing file."
                "'raise' will raise an error if the output file already exists."
            ),
        ),
    ] = OnExistingOutput.RAISE,
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
            "--model",
            "-m",
            help="Model name.",
        ),
    ] = "openai:gpt-4o-mini",
    examples: Annotated[
        Path | None,
        typer.Option(
            "--examples",
            help=(
                "Path to the examples file."
                " This should be a JSONL file with each line containing `HazmatLabeledItem`s."
                " If provided, the examples will be used to create an example store."
            ),
        ),
    ] = None,
    embedding_model_name: Annotated[
        str,
        typer.Option(
            "--embedding-model",
            help="Embedding model name.",
        ),
    ] = "google:models/gemini-embedding-exp-03-07",
    max_input_tokens: Annotated[
        int,
        typer.Option(
            "--max-input-tokens",
            help=(
                "Max input tokens."
                " This is the maximum number of tokens that can be sent to the model, and should be found in each provider's documentation."
                " Pass a smaller value than the official limit to avoid hitting the context window limit."
            ),
        ),
    ] = 16384,
    parallel_batches: Annotated[
        int,
        typer.Option(
            "--parallel-batches",
            help="Number of batches to process in parallel",
        ),
    ] = 1,
):
    if on_existing_output == OnExistingOutput.RAISE and output.exists():
        raise FileExistsError(f"Output file {output} already exists")

    dotenv.load_dotenv()

    if examples is not None:
        logger.info(f"Loading examples from {examples}")
        example_store = ExampleStore.from_embedding_model_name_and_persist_directory(
            persist_directory=examples.parent,
            embedding_model_name=embedding_model_name,
        )
        with examples.open() as f:
            example_store.add_batch(
                [HazmatLabeledItem.model_validate_json(line) for line in f]
            )
        agent = HazmatAgent.from_model(model_name, example_store=example_store)
    else:
        logger.info("No examples provided, initializing agent without example store")
        agent = HazmatAgent.from_model(model_name)

    with input.open() as f:
        items = [HazmatInputItem.model_validate_json(line) for line in f]

    items_to_process = list(items)

    # Handle existing output file
    if on_existing_output == OnExistingOutput.CONTINUE and output.exists():
        logger.info(f"Loading existing results from {output}")

        processed_item_ids = set()
        with output.open() as f:
            for line in f:
                existing_result = HazmatPrediction.model_validate_json(line)
                processed_item_ids.add(existing_result.item_id)

        logger.info(f"Found {len(processed_item_ids)} already processed items")
        items_to_process = [
            item for item in items_to_process if item.item_id not in processed_item_ids
        ]
        logger.info(f"Filtered to {len(items_to_process)} items still to process")

    output.parent.mkdir(parents=True, exist_ok=True)
    file_mode = "a" if on_existing_output == OnExistingOutput.CONTINUE else "w"
    logger.info(f"Opening output file in '{file_mode}' mode")

    tasks: set[asyncio.Task] = set()
    with output.open(file_mode) as f:
        while items_to_process or tasks:
            print(f"[cyan]Items to process:[/cyan] {len(items_to_process)}")
            print(f"[cyan]Pending tasks:[/cyan] {len(tasks)}")

            while items_to_process and len(tasks) < parallel_batches:
                batch = _extract_batch(
                    items_to_process,
                    batch_size=batch_size,
                    max_input_tokens=max_input_tokens,
                    batch_token_estimator=lambda batch: estimate_token_count(
                        agent.get_user_prompt_for_batch(batch),
                        "overestimate",
                    ),
                )
                tasks.add(asyncio.create_task(_process_batch(agent=agent, batch=batch)))

            done, tasks = await asyncio.wait(
                tasks,
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in done:
                batch, results = task.result()
                processed_ids = {result.item_id for result in results}
                print(f"    [blue]Processed IDs:[/blue] {processed_ids}")
                # Re-add items that were not processed
                items_to_process.extend(
                    item for item in batch if item.item_id not in processed_ids
                )
                for result in results:
                    f.write(result.model_dump_json() + "\n")


async def _process_batch(
    agent: HazmatAgent,
    batch: list[HazmatInputItem],
) -> tuple[list[HazmatInputItem], list[HazmatLabeledItem]]:
    try:
        print(f"[green]Classifying batch of {len(batch)} items...[/green]")
        result = await agent.classify_batch(
            batch,
            allow_mismatched_predictions=True,
        )
        return batch, result
    except Exception as e:
        logger.error(f"Error processing batch - trying again: {e}")
        return batch, []


def _extract_batch(
    items_to_process: list[HazmatInputItem],
    batch_size: int,
    max_input_tokens: int,
    batch_token_estimator: Callable[[list[HazmatInputItem]], int],
) -> list[HazmatInputItem]:
    items_to_batch = min(batch_size, len(items_to_process))
    batch = [items_to_process.pop() for _ in range(items_to_batch)]

    while (estimated_token_count := batch_token_estimator(batch)) > max_input_tokens:
        if len(batch) == 1:
            raise ValueError(
                f"Batch of {len(batch)} items is too large, and cannot be reduced further"
            )
        logger.warning(
            f"Estimated token count of {estimated_token_count} exceeds max input tokens of {max_input_tokens}"
        )
        logger.info(
            f"Batch of {len(batch)} items is too large, reducing to {len(batch) // 2}"
        )
        items_to_process.extend(batch[: len(batch) // 2])
        batch = batch[len(batch) // 2 :]

    return batch


if __name__ == "__main__":
    app()
