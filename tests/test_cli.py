"""Tests de integración de la CLI de GAFF."""

import json
from pathlib import Path
from typer.testing import CliRunner
from gaff.cli import app

runner = CliRunner()


def test_cli_version():
    res = runner.invoke(app, ["--version"])
    assert res.exit_code == 0
    assert "GAFF" in res.stdout


def test_cli_rules():
    res = runner.invoke(app, ["rules"])
    assert res.exit_code == 0
    assert "GAFF001" in res.stdout
    assert "GAFF005" in res.stdout


def test_cli_explain():
    res = runner.invoke(app, ["explain", "GAFF001"])
    assert res.exit_code == 0
    assert "snake_case" in res.stdout


def test_cli_check_limpio(tmp_path):
    fuente = tmp_path / "ok.c"
    fuente.write_text("int main(void) { return 0; }\n")

    res = runner.invoke(app, ["check", str(fuente)])
    assert res.exit_code == 0
    assert "cumplen con las reglas" in res.stdout


def test_cli_check_con_violaciones_y_json(tmp_path):
    fuente = tmp_path / "goto.c"
    fuente.write_text("int main(void) { goto end; end: return 0; }\n")

    res = runner.invoke(app, ["check", str(fuente), "--json"])
    assert res.exit_code == 1
    data = json.loads(res.stdout)
    assert data["ok"] is False
    assert data["total_violaciones"] >= 1
    assert any(v["codigo"] == "GAFF008" for a in data["archivos"] for v in a["violaciones"])


def test_cli_fix(tmp_path):
    fuente = tmp_path / "fixme.c"
    fuente.write_text("void f(void){\n    if(1){ return; }\n}\n")

    res = runner.invoke(app, ["fix", str(fuente)])
    assert "correcciones" in res.stdout
    assert "if (" in fuente.read_text(encoding="utf-8")
