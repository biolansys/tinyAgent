import unittest
from unittest.mock import patch

from openrouter_agent.providers import discovery


class DiscoveryTests(unittest.TestCase):
    def test_format_discovery_report_includes_provider_counts(self):
        report = {
            "source": "live",
            "last_checked": "2026-05-01T12:00:00",
            "use_cache": False,
            "early_stop": False,
            "max_checks_per_provider": 0,
            "candidate_counts": {"openrouter": 3, "huggingface": 2},
            "tested_counts": {"openrouter": 3, "huggingface": 2},
            "working_counts": {"openrouter": 2, "huggingface": 1},
            "failure_counts": {"openrouter": 1, "huggingface": 1},
            "working_routes": ["openrouter::a", "openrouter::b", "huggingface::c"],
            "failures": {"openrouter::x": "timeout", "huggingface::y": "unexpected response"},
        }
        with patch("openrouter_agent.providers.discovery.load_rankings", return_value={}):
            text = discovery.format_discovery_report(report)
        self.assertIn("openrouter: candidates=3 tested=3 working=2 failed=1", text)
        self.assertIn("huggingface: candidates=2 tested=2 working=1 failed=1", text)
        self.assertIn("openrouter::x: timeout", text)

    def test_candidate_routes_zero_max_checks_means_no_cap(self):
        with patch("openrouter_agent.providers.discovery.config.OPENROUTER_API_KEY", "key"), patch(
            "openrouter_agent.providers.discovery.config.HF_TOKEN", "token"
        ), patch(
            "openrouter_agent.providers.discovery.config.MISTRAL_API_KEY", "mkey"
        ), patch(
            "openrouter_agent.providers.discovery.fetch_openrouter_free_models",
            return_value=["or-1", "or-2", "or-3"],
        ), patch(
            "openrouter_agent.providers.discovery.get_hf_candidates",
            return_value=["hf-1", "hf-2"],
        ), patch(
            "openrouter_agent.providers.discovery.get_mistral_candidates",
            return_value=["mi-1", "mi-2"],
        ), patch("openrouter_agent.providers.discovery.rank_routes", side_effect=lambda routes: routes):
            routes = discovery.candidate_routes(max_checks_per_provider=0)

        self.assertEqual(
            [
                "openrouter::or-1",
                "openrouter::or-2",
                "openrouter::or-3",
                "huggingface::hf-1",
                "huggingface::hf-2",
                "mistral::mi-1",
                "mistral::mi-2",
            ],
            routes,
        )

    def test_test_route_requires_ok_response(self):
        with patch(
            "openrouter_agent.providers.discovery.post_json",
            return_value={"choices": [{"message": {"content": "something else"}}]},
        ), patch("openrouter_agent.providers.discovery.record_failure") as mock_failure, patch(
            "openrouter_agent.providers.discovery.record_success"
        ) as mock_success:
            ok, _latency, error = discovery.test_route("openrouter::model-a")

        self.assertFalse(ok)
        self.assertEqual("unexpected response", error)
        mock_success.assert_not_called()
        mock_failure.assert_called_once()

    def test_discover_routes_full_scan_does_not_stop_early(self):
        tested = []

        def fake_test_route(route):
            tested.append(route)
            return True, 0.1, ""

        with patch(
            "openrouter_agent.providers.discovery.candidate_routes",
            return_value=["r1", "r2", "r3", "r4"],
        ), patch(
            "openrouter_agent.providers.discovery.test_route", side_effect=fake_test_route
        ), patch("openrouter_agent.providers.discovery.rank_routes", side_effect=lambda routes: routes), patch(
            "openrouter_agent.providers.discovery.save_discovery_cache"
        ):
            routes = discovery.discover_routes(max_checks=0, target_working=1, use_cache=False, early_stop=False)

        self.assertEqual(["r1", "r2", "r3", "r4"], tested)
        self.assertEqual(["r1", "r2", "r3", "r4"], routes)

    def test_discover_routes_stores_last_report(self):
        with patch(
            "openrouter_agent.providers.discovery.candidate_routes",
            return_value=["openrouter::a", "huggingface::b"],
        ), patch(
            "openrouter_agent.providers.discovery.test_route",
            side_effect=[(True, 0.1, ""), (False, 0.0, "timeout")],
        ), patch("openrouter_agent.providers.discovery.rank_routes", side_effect=lambda routes: routes), patch(
            "pathlib.Path.write_text", autospec=True
        ):
            discovery.discover_routes(max_checks=0, use_cache=False, early_stop=False)

        report = discovery.last_discovery_report()
        self.assertIsNotNone(report)
        self.assertEqual("live", report["source"])
        self.assertEqual({"openrouter": 1, "huggingface": 1}, report["candidate_counts"])
        self.assertEqual({"huggingface": 1}, report["failure_counts"])


if __name__ == "__main__":
    unittest.main()
