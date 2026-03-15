import os
import unittest

from trading_bot.core.config import CredentialsConfig
from trading_bot.core.secrets import resolve_credentials


class SecretResolverTest(unittest.TestCase):
    def test_inline_credentials(self) -> None:
        resolved = resolve_credentials(
            CredentialsConfig(
                provider="inline",
                api_key="key",
                api_secret="secret",
            )
        )
        self.assertEqual(resolved.api_key, "key")
        self.assertEqual(resolved.api_secret, "secret")

    def test_env_credentials(self) -> None:
        os.environ["TEST_API_KEY"] = "env-key"
        os.environ["TEST_API_SECRET"] = "env-secret"
        try:
            resolved = resolve_credentials(
                CredentialsConfig(
                    provider="env",
                    api_key_env="TEST_API_KEY",
                    api_secret_env="TEST_API_SECRET",
                )
            )
        finally:
            os.environ.pop("TEST_API_KEY", None)
            os.environ.pop("TEST_API_SECRET", None)

        self.assertEqual(resolved.api_key, "env-key")
        self.assertEqual(resolved.api_secret, "env-secret")
