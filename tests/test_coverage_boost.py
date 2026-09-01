"""Tests adicionales para maximizar la cobertura en GAFF."""

import json
from pathlib import Path
from typer.testing import CliRunner
import gaff.cli
from gaff.cli import app
from gaff.core.linter import analizar_archivo, aplicar_autofix_archivo, ejecutar_linter
from gaff.core.models import ReporteLinting, ReporteArchivo, ViolacionRegla

runner = CliRunner()


def test_cli_check_rich_ok(tmp_path):
    fuente = tmp_path / "ok.c"
    fuente.write_text("int main(void)\n{\n    return 0;\n}\n")
    res = runner.invoke(app, ["check", str(fuente)])
    assert res.exit_code == 0
    assert "GAFF Linting OK" in res.stdout


def test_cli_check_rich_with_errors(tmp_path):
    fuente = tmp_path / "bad.c"
    fuente.write_text("int main(void) {\n    goto fin;\nfin:\n    return 0;\n}\n")
    res = runner.invoke(app, ["check", str(fuente)])
    assert res.exit_code == 1
    assert "violaciones de estilo" in res.stdout


def test_cli_fix_command(tmp_path):
    fuente = tmp_path / "fixme.c"
    fuente.write_text("int main(void) {\n\tif(1){\n\t\treturn 0;\n\t}\n}\n")
    res = runner.invoke(app, ["fix", str(fuente)])
    assert res.exit_code == 0
    assert "correcciones automáticas" in res.stdout


def test_cli_explain_command():
    res1 = runner.invoke(app, ["explain", "0x0007h"])
    assert res1.exit_code == 0
    assert "0x0007h" in res1.stdout

    res2 = runner.invoke(app, ["explain", "0x9999h"])
    assert res2.exit_code == 2


def test_cli_rules_command():
    res = runner.invoke(app, ["rules"])
    assert res.exit_code == 0
    assert "0x0007h" in res.stdout


def test_linter_nonexistent_and_directory(tmp_path):
    # Nonexistent file
    viols = analizar_archivo(tmp_path / "inexistente.c")
    assert len(viols) == 0

    # Directory with mixed files
    sub = tmp_path / "src"
    sub.mkdir()
    (sub / "a.c").write_text("int a;\n")
    (sub / "b.h").write_text("#ifndef B_H\n#define B_H\n#endif\n")
    (sub / "ignore.txt").write_text("ignorar\n")

    rep_dir = ejecutar_linter([sub])
    assert len(rep_dir.archivos) == 2


def test_linter_all_rules_trigger(tmp_path):
    # Long lines (0x0009h), long function (0x2005h), camelCase (0x0007h), typedef (0x3004h)
    fuente = tmp_path / "all_bad.c"
    long_line = "int " + "x" * 120 + " = 10;\n"
    lines = ["typedef struct nodo { int a; } MiNodo;\n"]
    lines.append("int miFuncionCamel(int param) {\n")
    lines.append(long_line)
    lines.extend([f"    int var_{i} = {i};\n" for i in range(55)])
    lines.append("    return 0;\n}\n")
    fuente.write_text("".join(lines), encoding="utf-8")

    rep = ejecutar_linter([fuente])
    codigos = [v.codigo for v in rep.archivos[0].violaciones]
    assert "0x0007h" in codigos
    assert "0x3004h" in codigos
    assert "0x2005h" in codigos
    assert "0x0009h" in codigos


def test_autofix_header_guard(tmp_path):
    header = tmp_path / "tipos.h"
    header.write_text("typedef struct { int x; } t_dato;\n")
    n = aplicar_autofix_archivo(header)
    assert n >= 1
    assert "#ifndef TIPOS_H" in header.read_text()

    # Non-existent
    assert aplicar_autofix_archivo(tmp_path / "no_existe.h") == 0


def test_cli_main_block(monkeypatch):
    monkeypatch.setattr("sys.argv", ["gaff", "--version"])
    try:
        gaff.cli.main()
    except SystemExit as e:
        assert e.code == 0


def test_cli_doctor():
    res = runner.invoke(app, ["doctor"])
    assert res.exit_code == 0
    assert "Diagnóstico del Entorno de GAFF" in res.stdout


def test_cli_export_rules(tmp_path):
    out = tmp_path / "rules.md"
    res = runner.invoke(app, ["export-rules", "-o", str(out)])
    assert res.exit_code == 0
    assert out.is_file()
    content = out.read_text(encoding="utf-8")
    assert "Manual de Convenciones y Estilo" in content
    assert "0x0007h" in content or "0x1001h" in content

