from feishu_notify.config import init_config
from feishu_notify.uninstall_flow import run_uninstall


def test_uninstall_removes_config(tmp_path, monkeypatch):
    cfg_dir = tmp_path / "fnotify"
    cfg_file = cfg_dir / "config.yaml"
    monkeypatch.setattr("feishu_notify.uninstall_flow.CONFIG_DIR", cfg_dir)
    monkeypatch.setattr("feishu_notify.uninstall_flow.CONFIG_FILE", cfg_file)
    monkeypatch.setattr("feishu_notify.config.CONFIG_DIR", cfg_dir)
    monkeypatch.setattr("feishu_notify.config.CONFIG_FILE", cfg_file)
    init_config()
    body = run_uninstall(yes=True, json_output=True)
    assert body["removed_fnotify"] is True
    assert not cfg_dir.exists()