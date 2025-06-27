from pathlib import Path
from typing import Annotated

import dotenv
import typer
from asyncer import runnify
from loguru import logger
from rich import print

from hazmate.agent.agent import HazmatAgent
from hazmate.input_datasets.input_items import HazmatInputItem
from hazmate.utils.tokens import estimate_token_count

app = typer.Typer()


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
):
    dotenv.load_dotenv()

    agent = HazmatAgent.from_model_and_mcp_servers(
        model_name=model_name,
        mcp_servers=(),
    )

    with input.open() as f:
        items = [HazmatInputItem.model_validate_json(line) for line in f]

    items_to_process = list(items)

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w") as f:
        while items_to_process:
            print(f"[cyan]Items to process:[/cyan] {len(items_to_process)}")

            if len(items_to_process) < batch_size:
                batch = items_to_process
                items_to_process = []
            else:
                batch = [items_to_process.pop() for _ in range(batch_size)]

            batch_prompt = agent.get_user_prompt_for_batch(
                batch,
                include_item_id=False,
                include_attributes=False,
            )
            while (
                estimated_token_count := estimate_token_count(
                    batch_prompt, "overestimate"
                )
            ) > max_input_tokens:
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
                batch_prompt = agent.get_user_prompt_for_batch(
                    batch,
                    include_item_id=False,
                    include_attributes=False,
                )

            try:
                print(f"[green]Classifying batch of {len(batch)} items...[/green]")
                results = await agent.classify_batch(
                    batch,
                    include_attributes=False,
                    allow_mismatched_predictions=True,
                )
                processed_ids = {result.item_id for result in results}
                print(f"    [blue]Processed IDs:[/blue] {processed_ids}")
                # Re-add items that were not processed
                items_to_process.extend(
                    item for item in batch if item.item_id not in processed_ids
                )
                for result in results:
                    f.write(result.model_dump_json() + "\n")
            except Exception as e:
                logger.error(f"Error processing batch - trying again: {e}")
                # Add items back to process list
                items_to_process.extend(batch)


if __name__ == "__main__":
    app()
