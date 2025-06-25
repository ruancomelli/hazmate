from pathlib import Path

import requests_cache

CACHE_DIR = Path(".cache")
# Install the cache before importing any modules that use the requests library
# I'm not sure why this is necessary, but it is - without it, the cache is not used
requests_cache.install_cache(str(CACHE_DIR / "requests"))

from examples.queries.interacting_with_meli_api import main as interacting_with_meli_api_main


def main():
    interacting_with_meli_api_main()


if __name__ == "__main__":
    main()
