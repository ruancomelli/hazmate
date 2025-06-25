from pprint import pprint
from typing import Any

from hazmate_builder.app_config import AppConfig
from hazmate_builder.auth import start_oauth_session
from hazmate_builder.queries.base import PaginatedReponseJson, paginate


def main():
    config = AppConfig.from_dotenv(".env")


if __name__ == "__main__":
    main()
