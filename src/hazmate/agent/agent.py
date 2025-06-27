"""Simple PydanticAI-based hazmat classification agent.

This module provides a straightforward implementation using PydanticAI
for hazmat detection with optional RAG tooling.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, Self, assert_never

from loguru import logger
from pydantic_ai import Agent, RunContext
from pydantic_ai.models import Model

from hazmate.agent.example_store import ExampleStore
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
class HazmatPredictionDeps:
    """Dependencies for the hazmat prediction agent."""

    example_store: ExampleStore | None = None


@dataclass(frozen=True)
class HazmatAgent:
    """Agent for hazmat classification with optional RAG enhancement."""

    agent: Agent[HazmatPredictionDeps, HazmatPrediction]
    deps: HazmatPredictionDeps

    @classmethod
    def from_model(
        cls,
        model_name: str | Model,
        example_store: ExampleStore | None = None,
    ) -> Self:
        """Create an agent from a model name with optional RAG functionality.

        Args:
            model_name: Model to use for predictions
            example_store: Optional example store for RAG functionality
        """
        agent = Agent(
            model_name,
            deps_type=HazmatPredictionDeps,
            output_type=HazmatPrediction,
            system_prompt=cls.get_system_prompt(
                include_examples_rag=example_store is not None
            ),
        )

        # Register RAG tool if example store is provided
        if example_store is not None:
            cls._register_example_retrieval_tool(agent)

        return cls(agent=agent, deps=HazmatPredictionDeps(example_store=example_store))

    @classmethod
    def _register_example_retrieval_tool(
        cls, agent: Agent[HazmatPredictionDeps, HazmatPrediction]
    ) -> None:
        """Register the example retrieval tool for RAG functionality."""

        @agent.tool
        async def retrieve_similar_examples(
            ctx: RunContext[HazmatPredictionDeps],
            item: HazmatInputItem,
            count: int = 3,
        ) -> str:
            """Retrieve similar hazmat classification examples to help with decision making.

            Args:
                ctx: The run context containing dependencies
                item: The product item to find similar examples for
                count: Number of examples to retrieve (default 3)

            Returns:
                Formatted string containing similar examples with their classifications
            """
            if ctx.deps.example_store is None:
                return "No example store available for similarity search."

            # Use the item directly for similarity search
            similar_examples = ctx.deps.example_store.retrieve(item, count=count)

            if not similar_examples:
                return "No similar examples found in the knowledge base."

            # Format the examples for the LLM
            formatted_examples = []
            for i, example in enumerate(similar_examples, 1):
                formatted_example = [
                    f"Example {i}:",
                    f"- Product: {example.name}",
                    f"- Classification: {'HAZMAT' if example.is_hazmat else 'NOT HAZMAT'}",
                    f"- Reason: {example.reason}",
                ]
                if example.traits:
                    formatted_example.append(
                        f"- Hazmat Traits: {', '.join(trait.trait_str for trait in example.traits)}"
                    )
                formatted_examples.append("\n".join(formatted_example))

            logger.info(f"Fetched {len(similar_examples)} similar examples")

            return "\n\n".join(formatted_examples)

    @classmethod
    def get_system_prompt(cls, include_examples_rag: bool = False) -> str:
        """Get the system prompt for the agent."""
        base_prompt = clean_text(
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
            """
        )

        if include_examples_rag:
            rag_instructions = clean_text(
                """
                    ENHANCED CLASSIFICATION WITH EXAMPLES:
                    You have access to a knowledge base of previously classified products through the retrieve_similar_examples tool.

                    CLASSIFICATION PROCESS:
                    1. First, use the retrieve_similar_examples tool, passing the complete item information
                    2. Analyze the product information considering the factors above
                    3. Compare with the similar examples found
                    4. Make your classification decision based on both the product analysis and similar examples
                    5. Provide a clear justification that references the similar examples when relevant

                    IMPORTANT: Always use the retrieve_similar_examples tool before making your final decision.
                """
            )
            base_prompt += "\n\n" + rag_instructions

        base_prompt += "\n\n" + clean_text(
            """
                Output schema:
                {output_schema}

                Always provide a clear, comprehensive justification for your decision.
                IMPORTANT: Always include the item_id in your response to maintain traceability.
            """
        ).format(output_schema=HazmatPrediction.model_json_schema())

        return base_prompt

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
        include_attributes: bool = True,
    ) -> str:
        """Get the user prompt for a batch of items."""
        return clean_text(
            """Analyze the following product information and classify each item as containing hazardous materials or not.

                {item_data}
            """
        ).format(
            item_data="\n".join(
                item.get_all_text_content_as_xml(include_attributes=include_attributes)
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
        result = await self.agent.run(
            prompt,
            deps=self.deps,
        )
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
        result = await self.agent.run(
            prompt,
            deps=self.deps,
            output_type=list[HazmatPrediction],
        )
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
