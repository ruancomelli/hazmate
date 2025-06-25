from pathlib import Path
from typing import Annotated, Self

import yaml
from pydantic import BaseModel, Field

from hazmate.builder.queries.categories import CategorySimple


class SubcategoryConfig(BaseModel):
    """Configuration for a subcategory."""

    id: str
    name: str


class IncludeCategoryConfig(CategorySimple):
    """Configuration for a category."""

    exclude_subcategories: Annotated[
        tuple[SubcategoryConfig, ...],
        Field(description="The subcategories to exclude."),
    ] = ()


class CategoryConfig(BaseModel):
    """Configuration for a category."""

    include: Annotated[
        tuple[IncludeCategoryConfig, ...],
        Field(description="The categories to include."),
    ] = ()
    exclude: Annotated[
        tuple[CategorySimple, ...],
        Field(description="The categories to exclude."),
    ] = ()


class CollectorConfig(BaseModel):
    """Configuration for the collector command."""

    categories: Annotated[
        CategoryConfig,
        Field(description="The categories to collect."),
    ]

    @classmethod
    def from_yaml(cls, path: Path) -> Self:
        with open(path, "r") as f:
            return cls.model_validate(yaml.safe_load(f))
