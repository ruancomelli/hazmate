"""Output dataset models for hazmat classification results."""

from typing import Annotated

from pydantic import BaseModel, Field

from hazmate.agent.hazmat_traits import HazmatTrait


class OutputDatasetItem(BaseModel):
    """Simple output format for hazmat classification results."""

    item_id: str = Field(description="Item ID from the input dataset")
    is_hazmat: bool = Field(description="Whether the item is classified as hazmat")
    traits: Annotated[
        list[HazmatTrait],
        Field(
            description="List of identified hazard traits, or empty if the item is not classified as hazmat"
        ),
    ] = []
    reason: str = Field(description="Free text justification for the classification")
