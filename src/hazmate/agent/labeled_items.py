"""This module contains the HazmatLabeledItem class, which is used to combine the input data and prediction result in a single object."""

from typing import Annotated, Self

from pydantic import BaseModel, Field

from hazmate.agent.hazmat_traits import HazmatTrait
from hazmate.agent.predictions import HazmatPrediction
from hazmate.input_datasets.input_items import HazmatInputItem


class MismatchedItemIdsError(ValueError):
    """Raised when the item ID of the input and prediction do not match."""

    def __init__(self, input_item_id: str, prediction_item_id: str):
        super().__init__(
            f"Item ID mismatch: input={input_item_id}, prediction={prediction_item_id}"
        )


class HazmatLabeledItem(BaseModel):
    """Combined input data and prediction result (X+Y).

    This includes all the input information plus the prediction,
    useful for creating evaluation datasets and CSV exports.
    """

    # Input data fields (from HazmatInputItem)
    item_id: Annotated[str, Field(description="Item ID from the input dataset")]
    name: Annotated[str, Field(description="Product name")]
    domain_id: Annotated[str, Field(description="Domain/category ID")]
    family_name: Annotated[str, Field(description="Product family name")]
    description: Annotated[str | None, Field(description="Product description")] = None
    short_description: Annotated[
        str | None,
        Field(description="Short product description"),
    ] = None
    keywords: Annotated[str | None, Field(description="Product keywords")] = None

    # Prediction results (from HazmatPrediction)
    is_hazmat: Annotated[
        bool,
        Field(description="Whether the item is classified as hazmat"),
    ]
    traits: Annotated[
        list[HazmatTrait],
        Field(
            description="List of identified hazard traits, or empty if the item is not classified as hazmat"
        ),
    ] = []
    reason: Annotated[
        str,
        Field(description="Free text justification for the classification"),
    ]

    @classmethod
    def from_input_and_prediction(
        cls,
        input_item: HazmatInputItem,
        prediction: HazmatPrediction,
    ) -> Self:
        """Create a HazmatLabeledItem from input data and prediction.

        Raises a `MismatchedItemIdsError` if the item IDs do not match.
        """
        # Verify IDs match
        if input_item.item_id != prediction.item_id:
            raise MismatchedItemIdsError(
                input_item_id=input_item.item_id,
                prediction_item_id=prediction.item_id,
            )

        return cls(
            # Input data
            item_id=input_item.item_id,
            name=input_item.name,
            domain_id=input_item.domain_id,
            family_name=input_item.family_name,
            description=input_item.description,
            short_description=input_item.short_description,
            keywords=input_item.keywords,
            # Prediction results
            is_hazmat=prediction.is_hazmat,
            traits=prediction.traits,
            reason=prediction.reason,
        )

    @property
    def input_item(self) -> HazmatInputItem:
        """The input item."""
        return HazmatInputItem(
            item_id=self.item_id,
            name=self.name,
            domain_id=self.domain_id,
            family_name=self.family_name,
            description=self.description,
            short_description=self.short_description,
        )

    @property
    def prediction(self) -> HazmatPrediction:
        """The prediction."""
        return HazmatPrediction(
            item_id=self.item_id,
            is_hazmat=self.is_hazmat,
            traits=self.traits,
            reason=self.reason,
        )
