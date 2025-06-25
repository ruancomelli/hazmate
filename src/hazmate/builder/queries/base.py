import enum

from pydantic import BaseModel, ConfigDict
from yarl import URL

BASE_URL = URL("https://api.mercadolibre.com")


class SiteId(enum.StrEnum):
    ARGENTINA = "MLA"
    BRAZIL = "MLB"


class ApiResponseModel(BaseModel):
    model_config = ConfigDict(frozen=True)
