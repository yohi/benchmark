from __future__ import annotations

import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from systemone_bench.provider_bench import (
    Provider,
    build_payload,
    load_providers,
    parse_thresholds,
    response_payload,
    select_providers,
    summarize_provider,
)


class ProviderBenchmarkTests(unittest.TestCase):
    def test_load_providers_supports_model_and_model_less_endpoints(self) -> None:
        payload = {
            "providers": [
                {
                    "name": "ollama",
                    "url": "http://localhost:11434/v1/systemone",
                    "model": "nimble",
                    "request_fields": {"keep_alive": "10m"},
                },
                {
                    "name": "strands",
                    "url": "http://localhost:8002/v1/systemone",
                },
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "providers.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            providers = load_providers(path)

        self.assertEqual(providers[0].model, "nimble")
        self.assertEqual(providers[1].model, None)
        self.assertEqual(
            providers[0].request_fields["keep_alive"],
            "10m",
        )

    def test_load_providers_rejects_duplicate_names(self) -> None:
        payload = {
            "providers": [
                {"name": "same", "url": "http://a"},
                {"name": "same", "url": "http://b"},
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "providers.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate provider"):
                load_providers(path)

    def test_load_providers_expands_environment_in_url_and_headers(self) -> None:
        payload = {
            "providers": [
                {
                    "name": "cloudflare",
                    "url": (
                        "https://api.cloudflare.com/client/v4/accounts/"
                        "${CF_ACCOUNT}/ai/run/@cf/cloudflare/clef-flash"
                    ),
                    "headers": {
                        "Authorization": "Bearer ${CF_TOKEN}",
                    },
                    "response_path": ["result"],
                }
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "providers.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with patch.dict(
                "os.environ",
                {"CF_ACCOUNT": "account-1", "CF_TOKEN": "secret-token"},
                clear=False,
            ):
                providers = load_providers(path)

        self.assertIn("account-1", providers[0].url)
        self.assertEqual(
            providers[0].headers["Authorization"],
            "Bearer secret-token",
        )
        self.assertEqual(providers[0].response_path, ("result",))

    def test_load_providers_rejects_unset_environment_reference(self) -> None:
        payload = {
            "providers": [
                {
                    "name": "cloudflare",
                    "url": "https://example.test/${MISSING_PROVIDER_TEST_ENV}",
                }
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "providers.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with patch.dict("os.environ", {}, clear=True):
                with self.assertRaisesRegex(ValueError, "unset environment"):
                    load_providers(path)

    def test_response_payload_unwraps_cloudflare_result_envelope(self) -> None:
        provider = Provider(
            name="cloudflare",
            url="https://example.test",
            response_path=("result",),
        )
        payload = response_payload(
            provider,
            {
                "result": {
                    "answers": {"route": {"choice": "review"}},
                    "usage": {"input_tokens": 123},
                },
                "success": True,
            },
        )
        self.assertEqual(payload["answers"]["route"]["choice"], "review")
        self.assertEqual(payload["usage"]["input_tokens"], 123)

    def test_build_payload_omits_model_for_server_bound_checkpoint(self) -> None:
        provider = Provider(
            name="strands",
            url="http://localhost:8002/v1/systemone",
        )
        payload = build_payload(
            provider,
            {"task": "review this"},
            {"route": {"type": "choice", "criteria": {"a": "A", "b": "B"}}},
        )
        self.assertNotIn("model", payload)

    def test_build_payload_includes_provider_specific_request_fields(self) -> None:
        provider = Provider(
            name="nimble",
            url="http://localhost:11434/v1/systemone",
            model="nimble",
            request_fields={"keep_alive": "10m"},
        )
        payload = build_payload(provider, "state", {"q": {"type": "noul"}})
        self.assertEqual(payload["model"], "nimble")
        self.assertEqual(payload["keep_alive"], "10m")

    def test_build_payload_rejects_reserved_overrides(self) -> None:
        provider = Provider(
            name="bad",
            url="http://localhost",
            request_fields={"model": "oops"},
        )
        with self.assertRaisesRegex(ValueError, "reserved"):
            build_payload(provider, "state", {"q": {"type": "noul"}})

    def test_select_providers_preserves_requested_order(self) -> None:
        providers = [
            Provider("a", "http://a"),
            Provider("b", "http://b"),
            Provider("c", "http://c"),
        ]
        selected = select_providers(providers, "c,a")
        self.assertEqual([provider.name for provider in selected], ["c", "a"])

    def test_parse_thresholds_validates_range(self) -> None:
        self.assertEqual(parse_thresholds("0.5,0.8"), [0.5, 0.8])
        with self.assertRaisesRegex(ValueError, "between 0 and 1"):
            parse_thresholds("1.1")

    def test_summarize_provider_reports_accuracy_latency_and_thresholds(self) -> None:
        details = [
            {
                "model": "p",
                "case_id": "1",
                "pass": 1,
                "latency_ms": 100.0,
                "correct": True,
                "confidence": 0.9,
                "expected": "implementation",
                "prediction": "implementation",
                "usage": {"input_tokens": 100, "total_tokens": 100},
            },
            {
                "model": "p",
                "case_id": "2",
                "pass": 1,
                "latency_ms": 200.0,
                "correct": False,
                "confidence": 0.4,
                "expected": "review",
                "prediction": "implementation",
                "usage": {"input_tokens": 200, "total_tokens": 200},
            },
        ]

        result = summarize_provider(details, "p", [0.8])

        self.assertEqual(result["requests"], 2)
        self.assertEqual(result["accuracy"], 0.5)
        self.assertEqual(result["latency_ms"]["p50"], 150.0)
        self.assertEqual(result["thresholds"]["0.8"]["coverage"], 0.5)
        self.assertEqual(result["thresholds"]["0.8"]["accuracy"], 1.0)
        self.assertEqual(
            result["confusion_matrix"]["review"]["implementation"],
            1,
        )
        self.assertEqual(result["usage"]["requests_with_usage"], 2)
        self.assertEqual(result["usage"]["totals"]["input_tokens"], 300)


if __name__ == "__main__":
    unittest.main()
