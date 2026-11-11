from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from urllib.parse import urlparse

from .registry import CITY_REGISTRY


def _is_official_url(url: str, city: str | None = None) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme != "https":
        return False
    if city is None:
        domains = (domain for config in CITY_REGISTRY.values() for domain in config.official_domains)
    else:
        config = CITY_REGISTRY.get(city)
        domains = iter(config.official_domains if config else ())
    return any(host == domain or host.endswith("." + domain) for domain in domains)


@dataclass(frozen=True)
class Policy:
    city: str
    valid_from: date
    valid_until: date
    weekday_groups: dict[int, frozenset[str]]
    source_url: str
    checked_at: datetime

    def is_valid_on(self, day: date) -> bool:
        return self.valid_from <= day <= self.valid_until

    def rotation_group_for(self, day: date) -> set[str] | None:
        """返回普通周一至周五对应的尾号组；不判断节假日或调休适用性。"""
        if not self.is_valid_on(day) or day.weekday() > 4:
            return None
        return set(self.weekday_groups[day.weekday()])

    def restricted_tails_for(self, day: date) -> set[str]:
        """兼容旧调用名；仅返回轮换表分组，不代表车辆实际受限。"""
        return self.rotation_group_for(day) or set()

    def to_dict(self) -> dict:
        return {
            "city": self.city,
            "valid_from": self.valid_from.isoformat(),
            "valid_until": self.valid_until.isoformat(),
            "weekday_groups": {str(k): sorted(v) for k, v in self.weekday_groups.items()},
            "source_url": self.source_url,
            "checked_at": self.checked_at.isoformat(),
        }


def validate_policy(payload: dict) -> Policy:
    try:
        city = str(payload["city"]).lower()
        start = date.fromisoformat(payload["valid_from"])
        end = date.fromisoformat(payload["valid_until"])
        groups_payload = payload["weekday_groups"]
        source_url = str(payload["source_url"])
        checked_at = datetime.fromisoformat(payload["checked_at"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"invalid policy payload: {exc}") from exc
    if city not in CITY_REGISTRY:
        raise ValueError(f"unsupported city: {city}")
    if end < start:
        raise ValueError("valid_until must not precede valid_from")
    if not _is_official_url(source_url, city):
        raise ValueError(f"source_url must use an official HTTPS domain for {city}")
    if checked_at.tzinfo is None:
        raise ValueError("checked_at must include a timezone")
    try:
        groups = {int(k): frozenset(str(t) for t in values) for k, values in groups_payload.items()}
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError("weekday_groups must map weekdays to tail lists") from exc
    if set(groups) != set(range(5)):
        raise ValueError("weekday_groups must define Monday through Friday")
    allowed = set("0123456789")
    if any(not tails or not tails <= allowed for tails in groups.values()):
        raise ValueError("each weekday must contain one or more digit tails")
    return Policy(city, start, end, groups, source_url, checked_at)
