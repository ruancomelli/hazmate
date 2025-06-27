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

from hazmate.agent.labeled_items import HazmatLabeledItem
from hazmate.agent.predictions import HazmatPrediction
from hazmate.input_datasets.input_items import HazmatInputItem
from hazmate.utils.text import clean_text


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

        # Run the agent
        result = await self.agent.run(prompt)
        prediction = result.output

        # Ensure the item_id is set correctly (in case the model didn't include it)
        if not prediction.item_id or prediction.item_id != item.item_id:
            prediction.item_id = item.item_id

        return prediction

    async def predict_batch(
        self,
        items: Sequence[HazmatInputItem],
        include_item_id: bool = True,
        include_attributes: bool = True,
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

        # If we don't have all predictions, fill in missing ones
        if len(predictions) != len(items) or prediction_ids != item_ids:
            # Create a mapping of predictions by ID
            pred_by_id = {
                pred.item_id: pred for pred in predictions if pred.item_id in item_ids
            }

            # Fill in missing predictions or fix IDs
            final_predictions = []
            for i, item in enumerate(items):
                if item.item_id in pred_by_id:
                    final_predictions.append(pred_by_id[item.item_id])
                elif i < len(predictions):
                    # Fix the ID for this prediction
                    pred = predictions[i]
                    pred.item_id = item.item_id
                    final_predictions.append(pred)
                else:
                    # Create a default prediction if missing
                    final_predictions.append(
                        HazmatPrediction(
                            item_id=item.item_id,
                            is_hazmat=False,
                            traits=[],
                            reason="Unable to classify - no prediction generated",
                        )
                    )

            return final_predictions

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
    ) -> list[HazmatLabeledItem]:
        """Classify multiple items and return combined input+prediction results."""
        predictions = await self.predict_batch(
            items,
            include_item_id=include_item_id,
            include_attributes=include_attributes,
        )

        if len(predictions) != len(items):
            raise ValueError(
                f"Number of predictions ({len(predictions)}) doesn't match number of items ({len(items)})"
            )

        return [
            HazmatLabeledItem.from_input_and_prediction(
                input_item=item,
                prediction=prediction,
            )
            for item, prediction in zip(items, predictions, strict=True)
        ]
