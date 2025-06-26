from pathlib import Path
from typing import Annotated, Self

import yaml
from pydantic import BaseModel, Field, model_validator

from hazmate.builder.queries.categories import CategorySimple


class SubcategoryConfig(BaseModel):
    """Configuration for a subcategory."""

    id: str
    name: str


class IncludeCategoryConfig(CategorySimple):
    """Configuration for a category."""

    queries: Annotated[
        tuple[str, ...],
        Field(
            description="The queries to use to search for products in this category."
        ),
    ]
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

    def get_include_ids(self) -> frozenset[str]:
        return frozenset(category.id for category in self.include)

    def get_exclude_ids(self) -> frozenset[str]:
        return frozenset(category.id for category in self.exclude)

    @model_validator(mode="after")
    def validate_include_and_exclude_are_disjoint(self) -> Self:
        include_ids = self.get_include_ids()
        exclude_ids = self.get_exclude_ids()
        if intersection := include_ids & exclude_ids:
            raise ValueError(
                f"Cannot include and exclude the same category: {intersection}"
            )
        return self


class CollectorConfig(BaseModel):
    """Configuration for the collector command."""

    categories: Annotated[
        CategoryConfig,
        Field(description="The categories to collect."),
    ]
    extra_queries: Annotated[
        tuple[str, ...],
        Field(
            description="The extra queries to use to search for products that are not in the categories queries."
        ),
    ] = ()

    @classmethod
    def from_yaml(cls, path: Path) -> Self:
        with open(path, "r") as f:
            return cls.model_validate(yaml.safe_load(f))
