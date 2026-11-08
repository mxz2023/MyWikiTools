from __future__ import annotations

from pathlib import Path

import pytest

from apple_health import ingest, store


@pytest.fixture()
def tmp_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(store, "DB_FILE", tmp_path / "health.db")
    monkeypatch.setattr(store, "DATA_DIR", tmp_path)


def test_ingest_json_quantities(tmp_db: None) -> None:
    doc = {
        "quantities": [
            {
                "uuid": "q1",
                "kind": "steps",
                "value": 50.0,
                "unit": "count",
                "start_at": "2025-11-07T10:00:00+00:00",
                "end_at": "2025-11-07T11:00:00+00:00",
            }
        ]
    }
    out = ingest.ingest_document(doc)
    assert out["upserted"]["quantities"] == 1
    rows = store.query_quantities(
        "steps", "2025-11-07T00:00:00+00:00", "2025-11-08T00:00:00+00:00"
    )
    assert rows[0]["value"] == 50.0
