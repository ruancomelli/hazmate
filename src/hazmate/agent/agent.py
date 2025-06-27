"""Simple PydanticAI-based hazmat classification agent.

This module provides a straightforward implementation using PydanticAI
for hazmat detection without complex RAG/MCP tooling.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, Self, assert_never

from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio
from pydantic_ai.models import Model

from hazmate.agent.labeled_items import HazmatLabeledItem, MismatchedItemIdsError
from hazmate.agent.predictions import HazmatPrediction
from hazmate.input_datasets.input_items import HazmatInputItem
from hazmate.utils.text import clean_text


class MismatchedPredictionsError(ValueError):
    """Error raised when predictions are missing for some items."""

    def __init__(self, input_ids: set[str], prediction_ids: set[str]):
        super().__init__(
            f"Requested predictions for {sorted(input_ids)} but only got {sorted(prediction_ids)} - missing {sorted(input_ids - prediction_ids)}"
        )
        self.input_ids = input_ids
        self.prediction_ids = prediction_ids


@dataclass(frozen=True)
class HazmatAgent:
    """Agent for hazmat classification."""

    agent: Agent[None, HazmatPrediction]

    @classmethod
    def from_model_and_mcp_servers(
        cls,
        model_name: str | Model,
        mcp_servers: tuple[MCPServerStdio, ...],
    ) -> Self:
        """Create an agent from a model name and MCP servers."""
        agent = Agent(
            model_name,
            output_type=HazmatPrediction,
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
            IMPORTANT: Always include the item_id in your response to maintain traceability.
        """
        ).format(output_schema=HazmatPrediction.model_json_schema())

    def get_user_prompt_for_item(
        self,
        item: HazmatInputItem,
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
        items: Sequence[HazmatInputItem],
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

    async def predict_item(
        self,
        item: HazmatInputItem,
        include_item_id: bool = True,
        include_attributes: bool = True,
        on_different_id: Literal["raise", "fix", "ignore"] = "raise",
    ) -> HazmatPrediction:
        """Predict hazmat classification for a single item.

        Args:
            item: The input dataset item to classify
            include_item_id: Whether to include item ID in the prompt
            include_attributes: Whether to include attributes in the prompt

        Returns:
            HazmatPrediction with classification results
        """
        prompt = self.get_user_prompt_for_item(
            item,
            include_item_id=include_item_id,
            include_attributes=include_attributes,
        )
        result = await self.agent.run(prompt)
        prediction = result.output

        if prediction.item_id != item.item_id:
            match on_different_id:
                case "raise":
                    raise MismatchedItemIdsError(
                        input_item_id=item.item_id,
                        prediction_item_id=prediction.item_id,
                    )
                case "fix":
                    prediction.item_id = item.item_id
                case "ignore":
                    pass
                case never:
                    assert_never(never)

        return prediction

    async def predict_batch(
        self,
        items: Sequence[HazmatInputItem],
        include_item_id: bool = True,
        include_attributes: bool = True,
        allow_mismatched_predictions: bool = False,
    ) -> list[HazmatPrediction]:
        """Predict hazmat classification for multiple items in batch."""
        prompt = clean_text(
            """Analyze the following product information and classify each item as containing hazardous materials or not.

                {item_data}

                For each input item above, you must provide a classification result with the corresponding item_id.
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
        result = await self.agent.run(prompt, output_type=list[HazmatPrediction])
        predictions = result.output

        # Ensure we have predictions for all items and IDs are correctly set
        item_ids = {item.item_id for item in items}
        prediction_ids = {pred.item_id for pred in predictions}
        if not allow_mismatched_predictions and prediction_ids != item_ids:
            raise MismatchedPredictionsError(
                input_ids=item_ids,
                prediction_ids=prediction_ids,
            )

        return predictions

    async def classify_item(
        self,
        item: HazmatInputItem,
        include_item_id: bool = True,
        include_attributes: bool = True,
    ) -> HazmatLabeledItem:
        """Classify a single item and return combined input+prediction result.

        Args:
            item: The input dataset item to classify
            include_item_id: Whether to include item ID in the prompt
            include_attributes: Whether to include attributes in the prompt

        Returns:
            HazmatLabeledItem with both input data and classification results
        """
        prediction = await self.predict_item(
            item,
            include_item_id=include_item_id,
            include_attributes=include_attributes,
        )

        return HazmatLabeledItem.from_input_and_prediction(
            input_item=item,
            prediction=prediction,
        )

    async def classify_batch(
        self,
        items: Sequence[HazmatInputItem],
        include_item_id: bool = True,
        include_attributes: bool = True,
        allow_mismatched_predictions: bool = False,
    ) -> list[HazmatLabeledItem]:
        """Classify multiple items and return combined input+prediction results.

        Args:
            items: The input dataset items to classify
            include_item_id: Whether to include item ID in the prompt
            include_attributes: Whether to include attributes in the prompt
            allow_mismatched_predictions: Whether to allow mismatched predictions
        """
        predictions = await self.predict_batch(
            items,
            include_item_id=include_item_id,
            include_attributes=include_attributes,
            allow_mismatched_predictions=allow_mismatched_predictions,
        )

        inputs_map = {item.item_id: item for item in items}
        predictions_map = {pred.item_id: pred for pred in predictions}

        return [
            HazmatLabeledItem.from_input_and_prediction(
                input_item=inputs_map[item_id],
                prediction=predictions_map[item_id],
            )
            for item_id in inputs_map
            if item_id in predictions_map
        ]
