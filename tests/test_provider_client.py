import unittest
from unittest.mock import patch

from openrouter_agent.providers import client


class ProviderClientTests(unittest.TestCase):
    def test_provider_url_supports_mistral(self):
        self.assertEqual("https://api.mistral.ai/v1/chat/completions", client.provider_url("mistral"))

    def test_headers_support_mistral(self):
        with patch("openrouter_agent.providers.client.config.MISTRAL_API_KEY", "mistral-key"):
            headers = client.headers("mistral")
        self.assertEqual("Bearer mistral-key", headers["Authorization"])
        self.assertEqual("application/json", headers["Content-Type"])

    def test_parse_route_supports_mistral_routes(self):
        provider, model = client.parse_route("mistral::mistral-small-latest")
        self.assertEqual("mistral", provider)
        self.assertEqual("mistral-small-latest", model)


if __name__ == "__main__":
    unittest.main()
