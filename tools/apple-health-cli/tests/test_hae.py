from __future__ import annotations

from pathlib import Path

import pytest

from apple_health import hae, store


@pytest.fixture()
def tmp_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(store, "DB_FILE", tmp_path / "health.db")
    monkeypatch.setattr(store, "DATA_DIR", tmp_path)


def test_hae_step_count(tmp_db: None) -> None:
    doc = {
        "data": {
            "metrics": [
                {
                    "name": "step_count",
                    "units": "count",
                    "data": [{"date": "2025-11-07 08:00:00 +0000", "qty": 9000, "source": "Watch"}],
                }
            ]
        }
    }
    out = hae.ingest_hae(doc)
    assert out["upserted"]["quantities"] == 1
    rows = store.query_quantities("steps", "2025-11-07T00:00:00+00:00", "2025-11-08T00:00:00+00:00")
    assert rows[0]["value"] == 9000.0
