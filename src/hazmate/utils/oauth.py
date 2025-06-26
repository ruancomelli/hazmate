"""An adapter for the `requests_oauthlib` library that ensures a cache is used."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Any, Self

import requests
from asyncer import asyncify
from pydantic import HttpUrl, SecretStr
from requests_oauthlib import OAuth2Session as _OAuth2Session
from yarl import URL


@dataclass(frozen=True)
class OAuth2Session:
    session: _OAuth2Session

    @classmethod
    def from_config(
        cls,
        client_id: str,
        client_secret: SecretStr,
        redirect_uri: str | HttpUrl | URL,
        auto_refresh_url: str | HttpUrl | URL,
        scopes: Iterable[str],
        oauth_token_loader: Callable[[], dict[str, Any] | None],
        oauth_token_saver: Callable[[dict[str, Any]], None],
    ) -> Self:
        if isinstance(redirect_uri, URL):
            redirect_uri = redirect_uri.human_repr()
        if isinstance(auto_refresh_url, URL):
            auto_refresh_url = auto_refresh_url.human_repr()

        session = _OAuth2Session(
            client_id,
            redirect_uri=str(redirect_uri),
            scope=list(scopes),
            token=oauth_token_loader(),
            token_updater=oauth_token_saver,
            auto_refresh_url=str(auto_refresh_url),
            auto_refresh_kwargs={
                "client_id": client_id,
                "client_secret": client_secret.get_secret_value(),
            },
        )

        return cls(session)

    async def get(
        self, url: str | URL, params: dict[str, Any] | None = None
    ) -> requests.Response:
        if isinstance(url, URL):
            url = url.human_repr()
        return await asyncify(self.session.get)(url, params=params)

    async def __aenter__(self) -> Self:
        self.session.__enter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.session.__exit__(exc_type, exc_value, traceback)
