"""Output dataset models for hazmat classification results."""

from typing import Annotated

from pydantic import BaseModel, Field

from hazmate.agent.hazmat_traits import HazmatTrait


class HazmatPrediction(BaseModel):
    """Prediction result from hazmat classification agent (Y only).

    This contains only the prediction/classification results,
    with the item_id to allow pairing with inputs.
    """

    item_id: Annotated[str, Field(description="Item ID to pair prediction with input")]
    is_hazmat: Annotated[
        bool, Field(description="Whether the item is classified as hazmat")
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
