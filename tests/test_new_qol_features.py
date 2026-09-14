"""Tests para las nuevas features QoL de GAFF."""

from pathlib import Path
from typer.testing import CliRunner
from gaff.cli import app
from gaff.core.linter import analizar_archivo
from gaff.core.config import cargar_configuracion_gaff
from gaff.core.interactive_fix import ejecutar_autofix_interactivo

runner = CliRunner()


def test_gaff_camel_case_function_detection(tmp_path: Path):
    src = tmp_path / "calc.c"
    src.write_text("int calcularPromedio(int a, int b) {\n    return (a + b) / 2;\n}\n")
    viols = analizar_archivo(src)
    codigos = [str(v.codigo) for v in viols]
    assert "0x0105h" in codigos or "0x000Eh" in [v.codigo for v in viols]


def test_gaff_obvious_comment_detection(tmp_path: Path):
    src = tmp_path / "comentarios.c"
    src.write_text("int main(void) {\n    int i = 0;\n    i++; // incrementa i en uno\n    return 0;\n}\n")
    viols = analizar_archivo(src)
    codigos = [str(v.codigo) for v in viols]
    assert "0x0203h" in codigos or "0x000Fh" in [v.codigo for v in viols]


def test_gaff_file_length_limit(tmp_path: Path):
    src = tmp_path / "largo.c"
    # Crear archivo con más de 500 líneas
    lines = ["int main(void) {"] + [f"    int x_{i} = {i};" for i in range(505)] + ["    return 0;", "}"]
    src.write_text("\n".join(lines))
    viols = analizar_archivo(src)
    codigos = [str(v.codigo) for v in viols]
    assert "0x0204h" in codigos or "0x0010h" in [v.codigo for v in viols]


def test_gaff_include_own_header_first(tmp_path: Path):
    hdr = tmp_path / "modulo.h"
    hdr.write_text("#pragma once\nvoid foo(void);\n")
    src = tmp_path / "modulo.c"
    src.write_text('#include <stdio.h>\n#include "otro.h"\n#include "modulo.h"\nvoid foo(void) {}\n')
    viols = analizar_archivo(src)
    codigos = [str(v.codigo) for v in viols]
    assert "0x0205h" in codigos or "0x0011h" in [v.codigo for v in viols]


def test_gaff_global_variable_static_rule(tmp_path: Path):
    src = tmp_path / "globals.c"
    src.write_text("int contador_invalido = 0;\nstatic int g_contador_ok = 0;\nint main(void) { return 0; }\n")
    viols = analizar_archivo(src)
    codigos = [str(v.codigo) for v in viols]
    assert "0x0106h" in codigos or "0x0012h" in [v.codigo for v in viols]


def test_gaff_interactive_fix(tmp_path: Path):
    src = tmp_path / "tabs.c"
    src.write_text("int main(void) {\n\tif(1){\n\t\treturn 0;\n\t}\n}\n")
    res = ejecutar_autofix_interactivo([src], auto_confirmar=True)
    assert res[str(src)] > 0
    assert "\t" not in src.read_text()


def test_gaff_config_loader(tmp_path: Path):
    cfg_file = tmp_path / ".gaffrc.yaml"
    cfg_file.write_text("max_line_length: 100\nmax_file_lines: 600\n")
    config = cargar_configuracion_gaff(tmp_path)
    assert config["max_line_length"] == 100
    assert config["max_file_lines"] == 600
