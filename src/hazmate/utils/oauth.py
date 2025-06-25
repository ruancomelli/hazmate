"""An adapter for the `requests_oauthlib` library that ensures a cache is used."""

from pathlib import Path

import requests_cache

CACHE_DIR = Path(".cache")
# Install the cache before importing any modules that use the requests library
# I'm not sure why this is necessary, but it is - without it, the cache is not used
requests_cache.install_cache(str(CACHE_DIR / "requests"))

from requests_oauthlib import OAuth2Session
