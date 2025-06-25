import enum

from yarl import URL

BASE_URL = URL("https://api.mercadolibre.com")


class SiteId(enum.StrEnum):
    ARGENTINA = "MLA"
    BRAZIL = "MLB"
