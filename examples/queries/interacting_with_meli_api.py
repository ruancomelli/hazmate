"""Example of how to use the search query."""

import textwrap
from pprint import pformat

from hazmate.builder.auth import start_oauth_session
from hazmate.builder.auth_config import AuthConfig
from hazmate.builder.queries.base import SiteId


def main():
    config = AuthConfig.from_dotenv(".env")

    with start_oauth_session(config) as session:
        for site_id in [SiteId.BRAZIL]:
            # Strange 403 Forbidden errors:
            print("Example of https://api.mercadolibre.com/sites/$SITE_ID/search")
            response = session.get(
                f"https://api.mercadolibre.com/sites/{site_id.value}/search",
                params={"q": "smartphone", "limit": 5},
            )
            response.raise_for_status()
            response_json = response.json()
            print(textwrap.indent(pformat(response_json), "    "))

            print(
                "Example of https://api.mercadolibre.com/sites/$SITE_ID/search?category=$CATEGORY_ID"
            )
            response = session.get(
                f"https://api.mercadolibre.com/sites/{site_id.value}/search",
                params={"category": "MLB1055", "limit": 3},  # Electronics category
            )
            response.raise_for_status()
            response_json = response.json()
            print(textwrap.indent(pformat(response_json), "    "))

            print("Example of https://api.mercadolibre.com/products/search")
            response = session.get(
                "https://api.mercadolibre.com/products/search",
                params={"q": "dinossauro", "site_id": site_id.value, "limit": 10},
            )
            response.raise_for_status()
            response_json = response.json()
            print(textwrap.indent(pformat(response_json), "    "))

            example_product_id = response_json["results"][0]["id"]

            print(
                "Example of https://api.mercadolibre.com/sites/$SITE_ID/search?category=$CATEGORY_ID"
            )
            user_id = session.token["user_id"]
            response = session.get(
                f"https://api.mercadolibre.com/users/{user_id}/items/search?category=MLB5672",
            )
            response.raise_for_status()
            response_json = response.json()
            print(textwrap.indent(pformat(response_json), "    "))

            print("Example of https://api.mercadolibre.com/products/$PRODUCT_ID")
            response = session.get(
                f"https://api.mercadolibre.com/products/{example_product_id}",
            )
            response.raise_for_status()
            response_json = response.json()
            print(textwrap.indent(pformat(response_json), "    "))

            print("Example of https://api.mercadolibre.com/items/$ITEM_ID/description")
            response = session.get(
                f"https://api.mercadolibre.com/items/{example_product_id}/description",
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
