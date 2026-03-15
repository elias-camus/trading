from __future__ import annotations

import json
import os
from dataclasses import dataclass

from trading_bot.core.config import CredentialsConfig


@dataclass
class ResolvedCredentials:
    api_key: str
    api_secret: str


def resolve_credentials(config: CredentialsConfig) -> ResolvedCredentials:
    if config.provider == "inline":
        if config.api_key is None or config.api_secret is None:
            raise ValueError("Inline credentials require api_key and api_secret")
        return ResolvedCredentials(api_key=config.api_key, api_secret=config.api_secret)

    if config.provider == "env":
        if config.api_key_env is None or config.api_secret_env is None:
            raise ValueError("Env credentials require api_key_env and api_secret_env")
        api_key = os.environ.get(config.api_key_env)
        api_secret = os.environ.get(config.api_secret_env)
        if api_key is None or api_secret is None:
            raise ValueError("Missing credential environment variables")
        return ResolvedCredentials(api_key=api_key, api_secret=api_secret)

    if config.provider == "aws_secrets_manager":
        if config.secret_name is None:
            raise ValueError("AWS Secrets Manager credentials require secret_name")
        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError("boto3 is required for aws_secrets_manager credentials") from exc
        session = boto3.session.Session(region_name=config.region)
        client = session.client("secretsmanager")
        response = client.get_secret_value(SecretId=config.secret_name)
        secret_string = response.get("SecretString")
        if secret_string is None:
            raise ValueError("SecretString was empty")
        payload = json.loads(secret_string)
        api_key = payload.get("api_key")
        api_secret = payload.get("api_secret")
        if not api_key or not api_secret:
            raise ValueError("Secret payload must include api_key and api_secret")
        return ResolvedCredentials(api_key=str(api_key), api_secret=str(api_secret))

    raise ValueError(f"Unsupported credentials provider: {config.provider}")
