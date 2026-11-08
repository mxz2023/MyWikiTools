from datetime import date
from pathlib import Path

import pytest

from mi_fitness import store


@pytest.fixture()
def temp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db = tmp_path / "health.db"
    data_dir = tmp_path / "share"
    data_dir.mkdir()
    monkeypatch.setattr(store, "DB_FILE", db)

    def _ensure() -> Path:
        return data_dir

    import mi_fitness.config as cfg

    monkeypatch.setattr(cfg, "ensure_data_dir", _ensure)
    store.init_db()
    return db


def test_upsert_steps(temp_db: Path) -> None:
    ins, upd = store.upsert_daily_activity(
        [{"day": "2026-03-01", "steps": 8000, "distance_m": 6000, "calories": 200, "raw": {}}]
    )
    assert ins == 1 and upd == 0
    ins2, upd2 = store.upsert_daily_activity(
        [{"day": "2026-03-01", "steps": 9000, "distance_m": 7000, "calories": 220, "raw": {}}]
    )
    assert ins2 == 0 and upd2 == 1
    rows = store.query_steps(date(2026, 3, 1), date(2026, 3, 1))
    assert rows[0]["steps"] == 9000


def test_weight_full(temp_db: Path) -> None:
    store.upsert_body(
        [
            {
                "id": "1710000000",
                "measured_at": "2026-03-01T08:00:00+00:00",
                "weight_kg": 70.5,
                "bmi": 22.1,
                "body_fat_pct": 18.2,
                "muscle_kg": None,
                "composition": {"visceral_fat": 5},
                "raw": {},
            }
        ]
    )
    rows = store.query_weight(date(2026, 3, 1), date(2026, 3, 1), full=True)
    assert rows[0]["body_fat_pct"] == 18.2
    assert rows[0]["composition"]["visceral_fat"] == 5
