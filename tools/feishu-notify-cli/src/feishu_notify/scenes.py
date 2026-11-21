from __future__ import annotations

import json
from importlib import resources
from pathlib import Path
from typing import Any

import yaml


def _scenes_root() -> Path:
    return Path(resources.files("feishu_notify")) / "builtin_scenes"


def list_scenes() -> list[dict[str, Any]]:
    root = _scenes_root()
    out: list[dict[str, Any]] = []
    if not root.is_dir():
        return out
    for manifest_path in sorted(root.glob("*/manifest.yaml")):
        data = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
        out.append(
            {
                "id": data.get("id") or manifest_path.parent.name,
                "version": data.get("version", "1.0"),
                "default_format": data.get("default_format", "auto"),
                "default_identity": data.get("default_identity", "auto"),
                "description": data.get("description", ""),
            }
        )
    return out


def load_manifest(scene_id: str, scene_version: str = "1.0") -> dict[str, Any]:
    root = _scenes_root() / scene_id
    manifest_path = root / "manifest.yaml"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"unknown scene: {scene_id}")
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    if str(data.get("version", "1.0")) != scene_version:
        # v0.1: only one version per directory; mismatch is a warning-level accept
        pass
    data["id"] = data.get("id") or scene_id
    data["_dir"] = str(root)
    return data


def manifest_template_path(manifest: dict[str, Any], kind: str) -> Path:
    name = manifest.get(f"{kind}_template")
    if not name:
        raise FileNotFoundError(f"scene {manifest.get('id')} has no {kind}_template")
    if str(name).startswith("shared/"):
        path = _scenes_root() / name
    else:
        path = Path(manifest["_dir"]) / name
    if not path.is_file():
        raise FileNotFoundError(f"missing template: {path}")
    return path


def describe_scene(scene_id: str) -> dict[str, Any]:
    manifest = load_manifest(scene_id)
    return {
        "id": manifest.get("id"),
        "version": manifest.get("version"),
        "description": manifest.get("description"),
        "default_format": manifest.get("default_format"),
        "default_identity": manifest.get("default_identity"),
        "required_fields": manifest.get("required_fields", []),
        "optional_fields": manifest.get("optional_fields", []),
    }