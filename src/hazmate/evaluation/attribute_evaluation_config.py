from functools import cache
from pathlib import Path
from typing import Self

import yaml
from pydantic import BaseModel, ConfigDict

from hazmate.input_datasets.input_items import HazmatInputItem


class HazmatAttribute(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    value: str
    tags: tuple[str, ...] = ()


class AttributeEvaluationConfig(BaseModel):
    """Configuration for attribute evaluation.

    Define the attributes that are considered hazmat. For example, a product
    that has the attribute "É inflamável: Sim" is considered hazmat.

    ```yaml
    hazmat_attributes:
    - name: É inflamável
      value: Sim
      tags:
      - INFLAMABLE

    - name: Com mercúrio
      value: Sim
      tags:
      - MERCURY

    - name: Tipo de termômetro
      value: De mercúrio
      tags:
      - MERCURY
    ```
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    hazmat_attributes: tuple[HazmatAttribute, ...]

    @classmethod
    def from_yaml_file(cls, config_path: Path) -> Self:
        """Load hazmat attributes configuration from YAML file."""
        with config_path.open() as f:
            config_data = yaml.safe_load(f)
        return cls.model_validate(config_data)

    def is_hazmat(self, item: HazmatInputItem) -> bool:
        """Check if an item is hazmat based on its attributes."""
        hazmat_attribute_pairs = self._generate_hazmat_attribute_pairs()
        return any(
            (item_attr.name, item_attr.value_name) in hazmat_attribute_pairs
            for item_attr in item.attributes
        )

    @cache
    def _generate_hazmat_attribute_pairs(self) -> frozenset[tuple[str, str]]:
        """Generate a set of hazmat attribute pairs."""
        return frozenset(
            (hazmat_attr.name, hazmat_attr.value)
            for hazmat_attr in self.hazmat_attributes
        )
