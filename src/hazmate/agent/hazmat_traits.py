import enum

from pydantic import BaseModel


class KnownHazmatTrait(enum.StrEnum):
    """Known hazmat traits."""

    # Physical hazards
    FLAMMABLE = "flammable"
    EXPLOSIVE = "explosive"
    OXIDIZING = "oxidizing"
    CORROSIVE = "corrosive"
    COMPRESSED_GAS = "compressed_gas"

    # Health hazards
    TOXIC = "toxic"
    CARCINOGENIC = "carcinogenic"
    IRRITANT = "irritant"
    SENSITIZING = "sensitizing"
    MUTAGENIC = "mutagenic"
    REPRODUCTIVE_TOXICITY = "reproductive_toxicity"

    # Environmental hazards
    AQUATIC_TOXICITY = "aquatic_toxicity"
    OZONE_DEPLETION = "ozone_depletion"

    # Special categories
    RADIOACTIVE = "radioactive"
    INFECTIOUS = "infectious"

    @property
    def trait_str(self) -> str:
        """Return the trait as a string."""
        return self.value


class OtherHazmatTrait(BaseModel):
    """Other hazmat traits not covered by the known traits."""

    trait: str

    @property
    def trait_str(self) -> str:
        """Return the trait as a string."""
        return self.trait


type HazmatTrait = KnownHazmatTrait | OtherHazmatTrait
