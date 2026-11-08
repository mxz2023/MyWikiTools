from dataclasses import dataclass

from mi_fitness import parsers


@dataclass
class FakeStep:
    date: str
    steps: int
    distance_m: int | None
    step_calories: int | None
    epoch_s: int = 0


def test_step_rows() -> None:
    rows = parsers.step_rows([FakeStep("2026-03-01", 5000, 4000, 150)])
    assert rows[0]["day"] == "2026-03-01"
    assert rows[0]["steps"] == 5000
