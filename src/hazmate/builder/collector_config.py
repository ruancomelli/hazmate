from typing import Annotated

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
        tuple[CategoryConfig, ...],
        Field(description="The categories to collect."),
    ]
