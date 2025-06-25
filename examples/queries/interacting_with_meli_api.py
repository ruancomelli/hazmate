"""Example of how to use the search query."""

import textwrap
from pprint import pformat

from hazmate_builder.app_config import AppConfig
from hazmate_builder.auth import start_oauth_session
from hazmate_builder.queries.base import SiteId


def main():
    config = AppConfig.from_dotenv(".env")

    with start_oauth_session(config) as session:
        for site_id in [SiteId.BRAZIL]:
            print("Example of https://api.mercadolibre.com/products/search")
            response = session.get(
                "https://api.mercadolibre.com/products/search",
                params={"q": "dinossauro", "site_id": site_id.value, "limit": 2},
            )
            response.raise_for_status()
            response_json = response.json()
            print(textwrap.indent(pformat(response_json), "    "))

            example_product_id = response_json["results"][0]["id"]

            print("Example of https://api.mercadolibre.com/products/$PRODUCT_ID")
            response = session.get(
                f"https://api.mercadolibre.com/products/{example_product_id}",
            )
            response.raise_for_status()
            response_json = response.json()
            print(textwrap.indent(pformat(response_json), "    "))

            print("Example of https://api.mercadolibre.com/sites/$SITE_ID/categories")
            response = session.get(
                f"https://api.mercadolibre.com/sites/{site_id.value}/categories",
            )
            response.raise_for_status()
            response_json = response.json()
            print(textwrap.indent(pformat(response_json), "    "))

            example_category_id = response_json[0]["id"]

            print("Example of https://api.mercadolibre.com/categories/$CATEGORY_ID")
            response = session.get(
                f"https://api.mercadolibre.com/categories/{example_category_id}",
            )
            response.raise_for_status()
            response_json = response.json()
            print(textwrap.indent(pformat(response_json), "    "))

            print(
                "Example of https://api.mercadolibre.com/categories/$CATEGORY_ID/attributes"
            )
            response = session.get(
                f"https://api.mercadolibre.com/categories/{example_category_id}/attributes",
            )
            response.raise_for_status()
            response_json = response.json()
            print(textwrap.indent(pformat(response_json), "    "))


if __name__ == "__main__":
    main()
