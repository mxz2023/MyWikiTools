"""Tests for SQLite store and export.xml import (no HealthKit)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from apple_health import import_xml, store


@pytest.fixture()
def tmp_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    db = tmp_path / "health.db"
    data = tmp_path / "data"
    monkeypatch.setattr(store, "DB_FILE", db)
    monkeypatch.setattr(store, "DATA_DIR", data)
    return db


def test_upsert_and_query_steps(tmp_db: Path) -> None:
    store.upsert_quantities(
        [
            {
                "uuid": "a1",
                "kind": "steps",
                "value": 100.0,
                "unit": "count",
                "start_at": "2024-06-01T00:00:00+00:00",
                "end_at": "2024-06-01T01:00:00+00:00",
                "source_name": "Watch",
                "source_bundle": "com.apple.health",
                "metadata_json": None,
            }
        ]
    )
    rows = store.query_quantities("steps", "2024-05-31T00:00:00+00:00", "2024-06-02T00:00:00+00:00")
    assert len(rows) == 1
    assert rows[0]["value"] == 100.0


def test_import_xml_minimal(tmp_db: Path, tmp_path: Path) -> None:
    xml_path = tmp_path / "export.xml"
    root = ET.Element(
        "HealthData",
        locale="en_US",
    )
    rec = ET.SubElement(
        root,
        "Record",
        type="HKQuantityTypeIdentifierStepCount",
        value="42",
        startDate="2024-06-01 08:00:00 +0000",
        endDate="2024-06-01 09:00:00 +0000",
        sourceName="iPhone",
    )
    tree = ET.ElementTree(root)
    tree.write(xml_path, encoding="UTF-8", xml_declaration=True)

    result = import_xml.import_export_xml(xml_path)
    assert result["skipped"] is False
    assert result["imported"]["quantities"] == 1
    rows = store.query_quantities("steps", "2024-05-31T00:00:00+00:00", "2024-06-02T00:00:00+00:00")
    assert rows[0]["value"] == 42.0

    again = import_xml.import_export_xml(xml_path)
    assert again["skipped"] is True
