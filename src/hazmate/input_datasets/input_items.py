from typing import Self

from pydantic import BaseModel
from pydantic import HttpUrl as Url

from hazmate.input_datasets.queries.product import (
    Attribute,
    MainFeature,
    Product,
)
from hazmate.input_datasets.queries.search import SearchResult


class InputDatasetAttribute(BaseModel):
    """Simplified product attribute for dataset."""

    id: str
    name: str
    value_name: str

    @classmethod
    def from_api_attribute(cls, attribute: Attribute) -> Self:
        return cls(
            id=attribute.id,
            name=attribute.name,
            value_name=attribute.value_name,
        )

    def to_text(self) -> str:
        return f"{self.name}: {self.value_name}"


class InputDatasetMainFeature(BaseModel):
    """Simplified main feature for dataset."""

    text: str
    type: str

    @classmethod
    def from_api_main_feature(cls, main_feature: MainFeature) -> Self:
        return cls(
            text=main_feature.text,
            type=main_feature.type,
        )

    def to_text(self) -> str:
        return self.text


class HazmatInputItem(BaseModel):
    """Dataset item containing relevant fields for Hazmat detection (X only).

    This combines information from both SearchResult and Product APIs
    to get the most comprehensive data for hazmat classification.
    """

    # Product identification
    item_id: str
    name: str
    domain_id: str
    family_name: str
    permalink: Url | None = None

    # Textual content (most important for Hazmat detection)
    description: str | None = None
    short_description: str | None = None
    keywords: str | None = None

    # Structured data
    attributes: tuple[InputDatasetAttribute, ...] = ()
    main_features: tuple[InputDatasetMainFeature, ...] = ()

    @classmethod
    def from_search_result_and_product(
        cls,
        search_result: SearchResult,
        product: Product,
    ) -> Self:
        """Create HazmatInputItem from both SearchResult and Product data.

        This combines the best information from both APIs:
        - SearchResult provides: keywords, description (detailed)
        - Product provides: short_description (basic), family_name, permalink
        """
        if search_result.id != product.id:
            raise ValueError(
                f"SearchResult ID ({search_result.id}) doesn't match Product ID ({product.id})"
            )

        api_attributes = product.attributes or search_result.attributes or ()
        attributes = tuple(
            map(
                InputDatasetAttribute.from_api_attribute,
                api_attributes,
            )
        )

        api_main_features = product.main_features or search_result.main_features or ()
        main_features = tuple(
            map(
                InputDatasetMainFeature.from_api_main_feature,
                api_main_features,
            )
        )

        return cls(
            item_id=product.id,
            name=product.name,
            domain_id=product.domain_id,  # Should be same in both
            family_name=product.family_name,
            permalink=product.permalink,
            # Textual content - combine from both sources
            description=search_result.description,
            short_description=product.short_description.content,
            keywords=search_result.keywords,
            attributes=attributes,
            main_features=main_features,
        )

    def get_all_text_content_as_xml(
        self,
        include_item_id: bool = True,
        include_attributes: bool = True,
    ) -> str:
        """Get all textual content concatenated for analysis."""
        content_parts = ["<item>"]

        if include_item_id:
            content_parts.append(f"<item_id>{self.item_id}</item_id>")

        if self.name:
            content_parts.append(f"<name>{self.name}</name>")

        if self.family_name:
            content_parts.append(f"<family_name>{self.family_name}</family_name>")

        description = (self.description or "").strip()
        if description:
            content_parts.append(f"<description>{description}</description>")

        short_description = (self.short_description or "").strip()
        if short_description:
            content_parts.append(
                f"<short_description>{short_description}</short_description>"
            )

        if self.keywords:
            content_parts.append(f"<keywords>{self.keywords}</keywords>")

        if include_attributes:
            # Add attributes
            for attr in self.attributes:
                if attr_text := attr.to_text().strip():
                    content_parts.append(f"<attribute>{attr_text}</attribute>")

            # Add main features
            for feature in self.main_features:
                if feature_text := feature.to_text().strip():
                    content_parts.append(f"<feature>{feature_text}</feature>")

        content_parts.append("</item>")

        return "\n".join(content_parts)
