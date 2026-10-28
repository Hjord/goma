import json
from pathlib import Path

import httpx
import pytest
from typer.testing import CliRunner

from goma import FileTokenStorage, GomaClient
from goma.cli import app

from .fake_goma import FakeGoma

runner = CliRunner()


@pytest.fixture(autouse=True)
def fake_cli(
    goma: FakeGoma, clock: FakeGoma, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GOMA_CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(
        "goma.cli.make_client",
        lambda: GomaClient(
            token_storage=FileTokenStorage(tmp_path / "session.json"),
            httpx_client=httpx.AsyncClient(transport=goma.transport()),
        ),
    )


def login(goma: FakeGoma) -> None:
    result = runner.invoke(app, ["login", "--email", "someone@example.com"], input=f"{goma.code}\n")
    assert result.exit_code == 0, result.output


def test_login_stores_a_private_session(goma: FakeGoma, tmp_path: Path) -> None:
    login(goma)

    session = tmp_path / "session.json"
    assert json.loads(session.read_text())["refresh_token"] == "refresh-1"
    assert session.stat().st_mode & 0o777 == 0o600


def test_login_with_a_wrong_code_fails(goma: FakeGoma) -> None:
    result = runner.invoke(app, ["login", "--email", "someone@example.com"], input="999999\n")

    assert result.exit_code == 1
    assert "invalid" in result.output


def test_commands_without_login_point_to_login() -> None:
    result = runner.invoke(app, ["lists"])

    assert result.exit_code == 1
    assert "goma login" in result.output


def test_lists_marks_the_primary(goma: FakeGoma) -> None:
    login(goma)

    result = runner.invoke(app, ["lists"])

    assert result.output.splitlines() == ["         7  Weekend", "*        3  Indkøbsliste"]


def test_items_defaults_to_the_primary_list(goma: FakeGoma) -> None:
    login(goma)

    result = runner.invoke(app, ["items"])

    assert result.output.splitlines() == [
        "[ ] 2 x Creme fraiche 38% fedt øko (Salling ØKO)  ·  Bilka 85164",
        "[ ] 1 x Salt  ·  no product",
        "[ ] 1 x Mælk (Arla)  ·  Netto",
    ]


def test_items_json_carries_the_article_number(goma: FakeGoma) -> None:
    login(goma)

    result = runner.invoke(app, ["items", "7", "--json"])

    [item] = json.loads(result.output)
    assert item["bilka_article_number"] == "37998"
    assert item["quantity"] == 1
