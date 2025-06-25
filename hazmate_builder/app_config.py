from pathlib import Path
from typing import Any, Self

import dotenv
from pydantic import BaseModel, ConfigDict, SecretStr
from pydantic import HttpUrl as Url


class AppConfig(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        frozen=True,
        extra="forbid",
    )

    dot_env_path: Path
    client_id: str
    client_secret: SecretStr
    redirect_url: Url

    @classmethod
    def from_dotenv(cls, dot_env_path: str | Path) -> Self:
        config_dict = dotenv.dotenv_values(dot_env_path)
        return cls.model_validate(
            {
                "dot_env_path": Path(dot_env_path),
                "client_id": _require_field(config_dict, "CLIENT_ID"),
                "client_secret": _require_field(config_dict, "CLIENT_SECRET"),
                "redirect_url": _require_field(config_dict, "REDIRECT_URL"),
            }
        )


def _require_field(config_dict: dict[str, Any], field: str) -> Any:
    value = config_dict.get(field)
    if not value:
        raise ValueError(f"Missing required config field: {field}")
    return value
