"""各城市适配器与官方域名的唯一注册表。新增城市时登记域名和来源函数名。"""
from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Callable


@dataclass(frozen=True)
class CityConfig:
    official_domains: tuple[str, ...]
    provider: str


CITY_REGISTRY: dict[str, CityConfig] = {
    "beijing": CityConfig(("beijing.gov.cn",), "fetch_beijing"),
    "tianjin": CityConfig(("tj.gov.cn",), "fetch_tianjin"),
}


def get_provider(city: str) -> Callable:
    config = CITY_REGISTRY.get(city)
    if config is None:
        raise ValueError(f"unsupported city: {city}")
    module = import_module(".sources", __package__)
    try:
        return getattr(module, config.provider)
    except AttributeError as exc:
        raise RuntimeError(f"source adapter is not implemented for {city}: {config.provider}") from exc
