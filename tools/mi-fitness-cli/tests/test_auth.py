"""Auth module imports (no network)."""

from mi_fitness.auth import LoginError, _render_qr_ascii


def test_login_error_type() -> None:
    assert issubclass(LoginError, Exception)


def test_render_qr_ascii() -> None:
    login = "https://c3.account.xiaomi.com/longPolling/login?ticket=lp_test"
    text = _render_qr_ascii(login)
    assert "█" in text or "##" in text or "▀" in text
