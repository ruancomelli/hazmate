import json
import textwrap
from functools import partial
from pathlib import Path
from typing import Any

import dotenv
from requests_oauthlib import OAuth2Session
from yarl import URL

from hazmate_builder.app_config import AppConfig

DOTENV_OAUTH_TOKEN_KEY = "OAUTH_TOKEN"
AUTHORIZATION_BASE_URL = URL("https://auth.mercadolivre.com.br/authorization")
REFRESH_URL = URL("https://api.mercadolibre.com/oauth/token")


def start_oauth_session(app_config: AppConfig) -> OAuth2Session:
    oauth_token_loader = partial(load_dotenv_oauth_token, app_config.dot_env_path)
    oauth_token_saver = partial(save_dotenv_oauth_token, app_config.dot_env_path)

    scopes = ["read", "offline_access"]
    session = OAuth2Session(
        app_config.client_id,
        redirect_uri=app_config.redirect_url,
        scope=scopes,
        token=oauth_token_loader(),
        token_updater=oauth_token_saver,
        auto_refresh_url=REFRESH_URL.human_repr(),
        auto_refresh_kwargs={
            "client_id": app_config.client_id,
            "client_secret": app_config.client_secret.get_secret_value(),
        },
    )

    if not session.token:
        print("No OAuth token found, fetching new one")

        auth_url, _state = session.authorization_url(
            AUTHORIZATION_BASE_URL.human_repr(),
        )

        authorization_code = input(
            textwrap.dedent(
                f"""
                    Please follow these steps to authorize the app:

                    1. Open the following URL in your browser:
                    {auth_url}
                    2. Copy the authorization code from the URL
                    3. Enter the authorization code here:
                """
            ).strip()
        )

        token = session.fetch_token(
            REFRESH_URL.human_repr(),
            code=authorization_code,
            client_secret=app_config.client_secret.get_secret_value(),
            include_client_id=True,
        )
        oauth_token_saver(token)

    return session


def load_dotenv_oauth_token(dot_env_path: Path) -> dict[str, Any] | None:
    json_str = dotenv.get_key(dot_env_path, DOTENV_OAUTH_TOKEN_KEY)
    return json.loads(json_str) if json_str else None


def save_dotenv_oauth_token(dot_env_path: Path, oauth_token: dict[str, Any]) -> None:
    dotenv.set_key(dot_env_path, DOTENV_OAUTH_TOKEN_KEY, json.dumps(oauth_token))
