"""Simple PydanticAI-based hazmat classification agent.

This module provides a straightforward implementation using PydanticAI
for hazmat detection without complex RAG/MCP tooling.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Self

from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio
from pydantic_ai.models import Model

from hazmate.agent.output_dataset import OutputDatasetItem
from hazmate.builder.input_dataset import InputDatasetItem
from hazmate.utils.text import clean_text


@dataclass(frozen=True)
class HazmatAgent:
    """Agent for hazmat classification."""

    agent: Agent[None, OutputDatasetItem]

    @classmethod
    def from_model_and_mcp_servers(
        cls,
        model_name: str | Model,
        mcp_servers: tuple[MCPServerStdio, ...],
    ) -> Self:
        """Create an agent from a model name and MCP servers."""
        agent = Agent(
            model_name,
            output_type=OutputDatasetItem,
            system_prompt=cls.get_system_prompt(),
            mcp_servers=mcp_servers,
        )
        return cls(agent)

    @classmethod
    def get_system_prompt(cls) -> str:
        """Get the system prompt for the agent."""
        return clean_text(
            """
            You are a hazardous materials (Hazmat) classification expert. Your job is to analyze product information and determine if items contain hazardous materials that require special handling during shipping.

            Hazardous materials include but are not limited to:

            - Flammable liquids, solids, and gases
            - Explosive materials and fireworks
            - Corrosive substances (acids, bases)
            - Toxic or poisonous materials
            - Radioactive materials
            - Compressed gases
            - Oxidizing agents
            - Infectious substances
            - Materials harmful to aquatic life

            Consider the following factors:

            1. Product name and description
            2. Chemical composition or ingredients
            3. Physical properties mentioned
            4. Intended use or application
            5. Safety warnings or precautions
            6. Regulatory classifications mentioned

            Be conservative in your classification - when in doubt about potential hazards, classify as hazmat for safety.

            Example hazard traits to identify: "flammable", "explosive", "corrosive", "toxic", "compressed_gas", "oxidizing", "radioactive", "infectious", "irritant", "carcinogenic", "environmental_hazard"

            Output schema:
            {output_schema}

            Always provide a clear, comprehensive justification for your decision.
        """
        ).format(output_schema=OutputDatasetItem.model_json_schema())

    def get_user_prompt_for_item(
        self,
        item: InputDatasetItem,
        include_item_id: bool = True,
        include_attributes: bool = True,
    ) -> str:
        # Format the item data for analysis
        item_data = item.get_all_text_content_as_xml(
            include_item_id=include_item_id,
            include_attributes=include_attributes,
        )

        # Create the prompt for this specific item
        prompt = clean_text(
            """Analyze the following product information and classify whether it contains hazardous materials:

                {item_data}
            """
        ).format(item_data=item_data)

        return prompt

    def get_user_prompt_for_batch(
        self,
        items: Sequence[InputDatasetItem],
        include_item_id: bool = True,
        include_attributes: bool = True,
    ) -> str:
        """Get the user prompt for a batch of items."""
        return clean_text(
            """Analyze the following product information and classify each item as containing hazardous materials or not.

                {item_data}
            """
        ).format(
            item_data="\n".join(
                item.get_all_text_content_as_xml(
                    include_item_id=include_item_id,
                    include_attributes=include_attributes,
                )
                for item in items
            )
        )

    async def classify_item(
        self,
        item: InputDatasetItem,
        verify_ids: bool = True,
        include_item_id: bool = True,
        include_attributes: bool = True,
    ) -> OutputDatasetItem:
        """Classify a single item for hazmat content.

        Args:
            item: The input dataset item to classify

        Returns:
            OutputDatasetItem with classification results
        """
        prompt = self.get_user_prompt_for_item(
            item,
            include_item_id=include_item_id,
            include_attributes=include_attributes,
        )

        # Run the agent
        result = await self.agent.run(prompt)

        # Ensure the ID matches the input (in case the model didn't use it correctly)
        output = result.output

        if verify_ids and output.item_id != item.item_id:
            raise ValueError(
                f"Item ID mismatch: {output.item_id} != {item.item_id}. The model did not use the item ID correctly."
            )

        return output

    async def classify_batch(
        self,
        items: Sequence[InputDatasetItem],
        verify_ids: bool = True,
        include_item_id: bool = True,
        include_attributes: bool = True,
    ) -> list[OutputDatasetItem]:
        """Classify multiple items in batch."""
        prompt = clean_text(
            """Analyze the following product information and classify each item as containing hazardous materials or not.

                {item_data}

                For each input item above, you must provide a classification with the same `item_id` as the corresponding input item.
            """
        ).format(
            item_data="\n".join(
                item.get_all_text_content_as_xml(
                    include_item_id=include_item_id,
                    include_attributes=include_attributes,
                )
                for item in items
            )
        )

        # Run the agent
        result = await self.agent.run(prompt, output_type=list[OutputDatasetItem])

        # Ensure the ID matches the input (in case the model didn't use it correctly)
        outputs = result.output

        output_ids = sorted(output.item_id for output in outputs)
        item_ids = sorted(item.item_id for item in items)
        if verify_ids and output_ids != item_ids:
            raise ValueError(
                "Item ID mismatch. The model did not use the item ID correctly. "
                f"Expected: {item_ids}, "
                f"Got: {output_ids}"
            )

        return outputs
