from __future__ import annotations

import json
import unittest
from unittest.mock import MagicMock, patch

from aifactory.llm import (
    ModelGatewayError,
    OpenAICompatibleGateway,
    _chat_completions_url,
    _parse_json_object,
)


class ModelGatewayTests(unittest.TestCase):
    def test_openrouter_base_url_is_not_double_versioned(self) -> None:
        self.assertEqual(
            _chat_completions_url("https://openrouter.ai/api/v1"),
            "https://openrouter.ai/api/v1/chat/completions",
        )

    def test_unversioned_gateway_gets_v1_path(self) -> None:
        self.assertEqual(
            _chat_completions_url("https://gateway.example.com"),
            "https://gateway.example.com/v1/chat/completions",
        )

    def test_parses_fenced_and_explained_json(self) -> None:
        self.assertEqual(_parse_json_object('```json\n{"status":"ok"}\n```'), {"status": "ok"})
        self.assertEqual(
            _parse_json_object('Result follows: {"status":"ok"} done'),
            {"status": "ok"},
        )

    def test_rejects_non_object_json(self) -> None:
        with self.assertRaises(ModelGatewayError):
            _parse_json_object('["ok"]')

    @patch("aifactory.llm.urllib.request.urlopen")
    def test_schema_and_completion_cap_are_sent_to_model(self, urlopen: MagicMock) -> None:
        response = MagicMock()
        response.read.return_value = json.dumps(
            {"choices": [{"message": {"content": '{"status":"ok"}'}}]}
        ).encode("utf-8")
        urlopen.return_value.__enter__.return_value = response
        gateway = OpenAICompatibleGateway(
            "https://gateway.example.com/v1",
            "test-key",
            "test-model",
            max_completion_tokens=321,
        )

        result = gateway.complete_json(
            "Return JSON.",
            "Connectivity test.",
            {"type": "object", "required": ["status"]},
        )

        self.assertEqual(result, {"status": "ok"})
        request = urlopen.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(payload["max_completion_tokens"], 321)
        self.assertIn('"required": ["status"]', payload["messages"][1]["content"])


if __name__ == "__main__":
    unittest.main()
