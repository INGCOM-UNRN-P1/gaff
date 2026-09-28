"""Reglas de separadores y asignaciones que miraban dentro de los literales (N-GAFF-06).

Tras N-GAFF-01, 0x000Ah (espacio antes de `,`/`;`), 0x0008h (operador coma
para encadenar asignaciones) y 0x0009h (notación húngara) seguían recorriendo
las líneas con los literales a la vista: `"uno ,dos"` o
`printf("x=%d, y=%d", a, b)` daban avisos en código correcto. Lo detectó el
caso `literales-opacos` del repositorio corpus.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from gaff.core.linter import analizar_archivo

REGLAS = {"0x000Ah", "0x0008h", "0x0009h"}


def _codigos(tmp_path: Path, cuerpo: str) -> list[str]:
    fuente = tmp_path / "prueba.c"
    fuente.write_text(f"#include <stdio.h>\n\nint main(void)\n{{\n{cuerpo}\n    return 0;\n}}\n", encoding="utf-8")
    return [v.codigo for v in analizar_archivo(fuente, reglas_habilitadas=REGLAS)]


@pytest.mark.parametrize("cuerpo", [
    '    const char *lista = "uno ,dos;tres ,  cuatro";',
    '    char separador = \' \'; char coma = \',\';',
    '    int r = printf("x=%d, y=%d", 1, 2);',
    '    int r = 0;\n    r = printf("x=%d, y=%d", 1, 2);',
    '    puts("int int_valor = 3;");',
])
def test_literales_no_generan_avisos(tmp_path, cuerpo):
    assert _codigos(tmp_path, cuerpo) == []


@pytest.mark.parametrize("cuerpo, esperado", [
    ("    int a = 1 , b = 2;", "0x000Ah"),
    ("    int a = 0;\n    int b = 0;\n    a = 1, b = 2;", "0x0008h"),
    ("    int int_valor = 3;", "0x0009h"),
])
def test_los_errores_reales_se_siguen_detectando(tmp_path, cuerpo, esperado):
    assert esperado in _codigos(tmp_path, cuerpo)
