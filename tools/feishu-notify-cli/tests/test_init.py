from pathlib import Path

from feishu_notify.config import load_config, save_dm_self_user_id


def test_save_dm_self_user_id(tmp_path: Path):
    cfg = tmp_path / "config.yaml"
    save_dm_self_user_id("ou_test123", path=cfg)
    data = load_config(cfg)
    assert data["routes"]["dm_self"]["user_id"] == "ou_test123"