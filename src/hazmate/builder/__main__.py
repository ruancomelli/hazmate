"""Main entry point for the hazmate builder package.

This script is used to build the hazmate dataset.
"""

from pathlib import Path

import requests_cache

CACHE_DIR = Path(".cache")
# Install the cache before importing any modules that use the requests library
# I'm not sure why this is necessary, but it is - without it, the cache is not used
requests_cache.install_cache(str(CACHE_DIR / "requests"))


def main():
    pass


if __name__ == "__main__":
    main()
