"""Tests de integración de la CLI de GAFF."""

import json
from pathlib import Path
from typer.testing import CliRunner
from gaff.cli import app

runner = CliRunner()


def test_cli_version():
    res = runner.invoke(app, ["--version"])
    assert res.exit_code == 0
    assert res.stdout.startswith("gaff ")  # formato común de yutani: «nombre versión»


def test_cli_rules():
    res = runner.invoke(app, ["rules"])
    assert res.exit_code == 0
    assert "0x0007h" in res.stdout
    assert "0x5003h" in res.stdout


def test_cli_explain():
    res = runner.invoke(app, ["explain", "0x0102h"])
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
    assert any(v["codigo"] == "0x1006h" for a in data["archivos"] for v in a["violaciones"])


def test_cli_fix(tmp_path):
    fuente = tmp_path / "fixme.c"
    fuente.write_text("void f(void){\n    if(1){ return; }\n}\n")

    res = runner.invoke(app, ["fix", str(fuente)])
    assert "correcciones" in res.stdout
    assert "if (" in fuente.read_text(encoding="utf-8")


def test_cli_check_recursivo(tmp_path):
    """Verifica que -r y --recursive recorran subdirectorios anidados."""
    dir_a = tmp_path / "modulo_a"
    dir_sub = dir_a / "submodulo"
    dir_sub.mkdir(parents=True)

    f_raiz = tmp_path / "raiz.c"
    f_raiz.write_text("int main(void) { return 0; }\n")

    f_anidado = dir_sub / "anidado.c"
    f_anidado.write_text("int f(void) { goto salir; salir: return 0; }\n")

    # Sin recursión sobre tmp_path (solo raiz.c en primer nivel)
    res_no_rec = runner.invoke(app, ["check", str(tmp_path)])
    assert res_no_rec.exit_code == 0
    assert "1" in res_no_rec.stdout

    # Con flag corto -r
    res_r = runner.invoke(app, ["check", str(tmp_path), "-r", "--json"])
    assert res_r.exit_code == 1
    data_r = json.loads(res_r.stdout)
    assert len(data_r["archivos"]) == 2
    assert any("anidado.c" in a["archivo"] for a in data_r["archivos"])

    # Con flag largo --recursive
    res_rec = runner.invoke(app, ["check", str(tmp_path), "--recursive", "--json"])
    assert res_rec.exit_code == 1
    data_rec = json.loads(res_rec.stdout)
    assert len(data_rec["archivos"]) == 2


def test_cli_fix_recursivo(tmp_path):
    """Verifica que fix -r aplique correcciones en subdirectorios."""
    sub_dir = tmp_path / "sub"
    sub_dir.mkdir(parents=True)
    f_sub = sub_dir / "fix_sub.c"
    f_sub.write_text("void f(void){\n    if(1){ return; }\n}\n")

    res = runner.invoke(app, ["fix", str(tmp_path), "-r"])
    assert res.exit_code == 0
    assert "correcciones" in res.stdout
    assert "if (" in f_sub.read_text(encoding="utf-8")



def test_check_de_un_archivo_que_no_existe_es_un_error_de_uso(tmp_path, monkeypatch):
    """N-GAFF-07: `gaff check mian.c` (nombre mal escrito) respondía «✓ Todos los archivos (0) cumplen»."""
    monkeypatch.chdir(tmp_path)
    res = runner.invoke(app, ["check", "mian.c"], env={"COLUMNS": "200"})
    assert res.exit_code == 2
    assert "mian.c" in res.output
    assert "cumplen" not in res.output


def test_check_sin_archivos_c_avisa_en_lugar_de_aprobar(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.c").write_text("int main(void)\n{\n    return 0;\n}\n", encoding="utf-8")
    res = runner.invoke(app, ["check", str(tmp_path)], env={"COLUMNS": "200"})
    assert res.exit_code == 0  # el hook de pre-commit corre `gaff check .`: no puede bloquear
    assert "No se encontró ningún archivo C" in res.output and "--recursive" in res.output
    assert "Todos los archivos" not in res.output

    res = runner.invoke(app, ["check", str(tmp_path), "--json"])
    datos = json.loads(res.stdout)
    assert datos["total_archivos"] == 0 and "advertencia" in datos

    res = runner.invoke(app, ["check", str(tmp_path), "--recursive", "--json"])
    assert "advertencia" not in json.loads(res.stdout)
