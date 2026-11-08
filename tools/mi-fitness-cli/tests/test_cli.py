from typer.testing import CliRunner

from mi_fitness.cli import app

runner = CliRunner()


def test_setup_human() -> None:
    result = runner.invoke(app, ["setup"])
    assert result.exit_code == 0
    assert "mfp login" in result.stdout


def test_setup_json() -> None:
    result = runner.invoke(app, ["setup", "--json-output"])
    assert result.exit_code == 0
    assert '"steps"' in result.stdout


def test_status_no_session() -> None:
    result = runner.invoke(app, ["status", "--json-output"])
    assert result.exit_code == 0
    assert "logged_in" in result.stdout
