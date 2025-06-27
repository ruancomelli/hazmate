from pydantic import BaseModel, ConfigDict


class HazmatAttribute(BaseModel):
    name: str
    value: str
    tags: list[str] = []


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

    hazmat_attributes: list[HazmatAttribute]
