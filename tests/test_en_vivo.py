"""`gaff check --stdin`: el linter en caliente de jonesy (Ola 7 de la hoja de ruta).

El texto llega por la entrada estándar (el buffer sin guardar), se analiza como si fuera el
archivo de --stdin-filename (con la configuración y las reglas ignoradas de su TP) y no se
informa lo que está a medio escribir.
"""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from gaff.cli import app
from gaff.core.linter import analizar_en_vivo, linea_inconclusa

runner = CliRunner()

CABECERA = "/**\n * Programa.\n */\n#include <stdio.h>\n#include <stdlib.h>\n\n"
INCONCLUSO = CABECERA + (
    "/**\n * Procesa.\n */\n"
    "int procesar(int n)\n"
    "{\n"
    "    int *datos = malloc(n * sizeof *datos);\n"
    "    int miContador = 0;\n"
    "    if (n > 0)\n"
    "    {\n"
)


@pytest.mark.parametrize("codigo, linea", [
    ("int main(void)\n{\n    return 0;\n}\n", None),
    ("int main(void)\n{\n    if (x)\n    {\n", 2),
    ("int f(void)\n{\n}\n}\n", 4),
    ("int main(void)\n{\n    printf(\"hola);\n}\n", 3),
    ("/* sin cerrar\nint x;\n", 1),
    ("#define MAX(a, b) ((a) > (b) ? \\\n    (a) : (b)\nint x = MAX(1, 2);\n", None),
    ("#if defined(X\nint y;\n", None),
    ("int n = 1'000'000;\nchar c = ')';\nconst char *s = \"}\\\"\";\n", None),
    ("// una llave { en un comentario\nint z;\n", None),
])
def test_linea_inconclusa(codigo, linea):
    assert linea_inconclusa(codigo) == linea


def test_en_vivo_no_informa_lo_que_falta_escribir(tmp_path):
    ruta = tmp_path / "tp" / "procesar.c"  # no existe: el texto viene del editor
    codigos = {str(v.codigo) for v in analizar_en_vivo(INCONCLUSO, ruta).archivos[0].violaciones}
    # El malloc sin verificar NULL todavía puede verificarse en la línea siguiente…
    assert "0x3001h" not in codigos
    # …pero el nombre en camelCase ya está escrito y vale igual (regla de una línea).
    assert "0x0102h" in codigos
    assert not ruta.exists()


def test_en_vivo_sin_la_linea_que_se_edita(tmp_path):
    codigo = CABECERA + "int main(void)\n{\n    int Total = 0;\n    return Total;\n}\n"
    ruta = tmp_path / "main.c"
    todas = analizar_en_vivo(codigo, ruta).archivos[0].violaciones
    assert any(v.linea == 9 for v in todas)
    assert not any(v.linea == 9 for v in analizar_en_vivo(codigo, ruta, 9).archivos[0].violaciones)


def test_en_vivo_con_las_reglas_del_tp(tmp_path):
    """El TP activo es el de --stdin-filename: su ripley.toml (aunque esté más arriba) y su
    .gaffrc.yaml filtran lo mismo que al guardar."""
    tp = tmp_path / "tp1"
    (tp / "ej1").mkdir(parents=True)
    (tmp_path / ".git").mkdir()
    codigo = CABECERA + "int main(void){\n    int Total = 0;\n    return Total;\n}\n"
    ruta = tp / "ej1" / "main.c"
    antes = {str(v.codigo) for v in analizar_en_vivo(codigo, ruta).archivos[0].violaciones}
    assert {"0x0007h", "0x0102h"} <= antes
    (tp / "ripley.toml").write_text('[reglas]\nignorar = ["gaff:0x0007h", "kaneda:0x0102h"]\n')
    (tp / ".gaffrc.yaml").write_text("excluded_rules: ['0x0206h']\n")
    despues = {str(v.codigo) for v in analizar_en_vivo(codigo, ruta).archivos[0].violaciones}
    assert "0x0007h" not in despues and "0x0206h" not in despues
    assert "0x0102h" in despues  # el patrón de kaneda no es de gaff


def test_ripley_toml_tambien_al_guardar(tmp_path, monkeypatch):
    """`gaff check archivo` (lo que jonesy corre al guardar) filtra lo mismo que en vivo."""
    (tmp_path / "ripley.toml").write_text('[reglas]\nignorar = ["0x00*7h"]\n')
    (tmp_path / "main.c").write_text(CABECERA + "int main(void){\n    return 0;\n}\n")
    monkeypatch.chdir(tmp_path)
    datos = json.loads(runner.invoke(app, ["check", "main.c", "--json"]).stdout)
    assert "0x0007h" not in {h["codigo"] for h in datos["hallazgos"]}


def test_cli_stdin_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "tp").mkdir()
    r = runner.invoke(app, ["check", "--stdin", "--stdin-filename", str(tmp_path / "tp" / "m.c"), "--json",
                            "--linea", "12"], input=INCONCLUSO)
    datos = json.loads(r.stdout)
    assert datos["hallazgos"], r.stdout
    assert {h["archivo"] for h in datos["hallazgos"]} == {"tp/m.c"}
    assert all(h.get("explicacion") for h in datos["hallazgos"])
    assert not (tmp_path / "tp" / "m.c").exists()


@pytest.mark.parametrize("args", [["--stdin", "--fix"], ["--stdin", "otro.c"], []])
def test_cli_stdin_combinaciones_invalidas(tmp_path, monkeypatch, args):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "otro.c").write_text("int x;\n")
    r = runner.invoke(app, ["check", *args], input="int y;\n")
    assert r.exit_code == 2
