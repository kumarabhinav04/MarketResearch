from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from aifactory.database import Database
from aifactory.sources.catalog import SourceCatalog
from aifactory.sources.http import SourceHttpClient, SourceRequestError
from aifactory.sources.service import _company_search_aliases, _name_similarity
from aifactory.sources.storage import RawSnapshotStore


ROOT = Path(__file__).resolve().parents[1]


class SourceCatalogTests(unittest.TestCase):
    def test_catalog_exposes_secret_names_but_never_values(self) -> None:
        catalog = SourceCatalog.load(ROOT / "config" / "sources.json")
        with patch.dict(os.environ, {"EIA_API_KEY": "do-not-expose"}):
            public = catalog.get("eia").public_dict()
        self.assertEqual(public["credential_env"], "EIA_API_KEY")
        self.assertTrue(public["credential_configured"])
        self.assertNotIn("do-not-expose", json.dumps(public))

    def test_optional_credential_is_not_reported_as_present(self) -> None:
        catalog = SourceCatalog.load(ROOT / "config" / "sources.json")
        with patch.dict(os.environ, {}, clear=True):
            public = catalog.get("openfigi").public_dict()
        self.assertTrue(public["credential_optional"])
        self.assertFalse(public["credential_configured"])

    def test_company_aliases_are_configuration_driven(self) -> None:
        aliases = _company_search_aliases(
            {"legal_name": "NVIDIA CORP", "ticker": "NVDA"},
            {"legal_suffixes": ["corp"], "include_ticker": True},
        )
        self.assertEqual(aliases, ["NVIDIA", "NVDA"])
        self.assertEqual(
            _name_similarity("NVIDIA CORP", "NVIDIA CORPORATION", {"corp", "corporation"}),
            1.0,
        )


class RawSnapshotTests(unittest.TestCase):
    def test_content_addressing_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = RawSnapshotStore(Path(directory))
            first = store.put(
                "test",
                b'{"ok":true}',
                source_url="https://example.com/data",
                content_type="application/json",
                external_id="one",
            )
            second = store.put(
                "test",
                b'{"ok":true}',
                source_url="https://example.com/data",
                content_type="application/json",
                external_id="one",
            )
            self.assertEqual(first.content_hash, second.content_hash)
            self.assertEqual(first.content_path, second.content_path)
            self.assertTrue(first.manifest_path.exists())


class SourceDatabaseTests(unittest.TestCase):
    def test_sync_cursor_and_identifiers_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Database(Path(directory) / "test.db")
            database.initialize()
            database.upsert_company(
                {
                    "id": "issuer",
                    "legal_name": "Issuer Inc",
                    "ticker": "ISS",
                    "exchange": "NYSE",
                    "security_id": "CIK1",
                    "segment": "power",
                    "subsegment": "switchgear",
                }
            )
            database.upsert_entity_identifier("issuer", "lei", "ABC", "gleif", 0.9)
            database.upsert_source_cursor("gleif", "company:issuer", {"lei": "ABC"})
            sync_id = database.create_source_sync(
                "gleif", "company:issuer", {"before": True}
            )
            database.complete_source_sync(
                sync_id,
                "completed",
                {"matches": 1},
                {"lei": "ABC"},
            )
            self.assertEqual(
                database.list_entity_identifiers("issuer")[0]["value"], "ABC"
            )
            self.assertEqual(
                database.get_source_cursor("gleif", "company:issuer"), {"lei": "ABC"}
            )
            self.assertEqual(database.list_source_syncs("gleif")[0]["status"], "completed")


class HttpBoundaryTests(unittest.TestCase):
    def test_query_credential_is_sent_but_not_returned(self) -> None:
        catalog = SourceCatalog.load(ROOT / "config" / "sources.json")
        definition = catalog.get("eia")

        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.url.params["api_key"], "secret-value")
            return httpx.Response(200, json={"ok": True})

        with patch.dict(os.environ, {"EIA_API_KEY": "secret-value"}):
            with patch("aifactory.sources.http.validate_external_url"):
                with SourceHttpClient(
                    definition,
                    "test-agent",
                    transport=httpx.MockTransport(handler),
                ) as client:
                    response = client.request("GET", "/v2/electricity")
        self.assertEqual(response.json(), {"ok": True})
        self.assertNotIn("secret-value", response.url)

    def test_response_size_limit_is_enforced(self) -> None:
        catalog = SourceCatalog.load(ROOT / "config" / "sources.json")
        definition = catalog.get("gleif")

        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"x" * (definition.max_response_bytes + 1))

        with patch("aifactory.sources.http.validate_external_url"):
            with SourceHttpClient(
                definition,
                "test-agent",
                transport=httpx.MockTransport(handler),
            ) as client:
                with self.assertRaises(SourceRequestError):
                    client.request("GET", "/too-large")


if __name__ == "__main__":
    unittest.main()
