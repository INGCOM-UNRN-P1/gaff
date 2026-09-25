"""Los literales no deben generar avisos de espaciado (N-GAFF-01).

La máscara de literales reemplazaba cada literal, comillas incluidas, por
espacios: `(c != 'a')` llegaba a las reglas como `(c !=    )` y
`printf("%d", x)` como `printf(    , x)`, disparando 0x000Eh (espacio junto a
paréntesis), 0x000Fh (espacios múltiples) y 0x000Dh/0x0015h (coma) en código
correcto.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from gaff.core.contexto import MARCA_LITERAL, enmascarar_literales_opacos
from gaff.core.linter import analizar_archivo

REGLAS_ESPACIADO = {"0x000Ah", "0x000Dh", "0x000Eh", "0x000Fh", "0x0015h"}


def _codigos(tmp_path: Path, codigo: str) -> list[tuple[int, str]]:
    fuente = tmp_path / "prueba.c"
    fuente.write_text(codigo, encoding="utf-8")
    return [(v.linea, v.codigo) for v in analizar_archivo(fuente, reglas_habilitadas=REGLAS_ESPACIADO)]


@pytest.mark.parametrize(
    "linea",
    [
        "    return (*p != 'a');",
        "    return (*p != '\\0');",
        "    if (c == ' ')",
        "    printf(\"total: %d\\n\", total);",
        "    printf(\"%s, %s\\n\", \"a\", \"b\");",
        "    char separador = ',';",
        "    return (x > 0) ? x : (s[0] == 'x');",
        "    char *msg = \"dos  espacios dentro del literal\";",
    ],
)
def test_literales_correctos_no_generan_avisos(tmp_path: Path, linea: str):
    codigo = f"int f(const char *p, char c, int x, int total, const char *s)\n{{\n{linea}\n}}\n"
    assert _codigos(tmp_path, codigo) == []


@pytest.mark.parametrize(
    ("linea", "esperado"),
    [
        ("    int  y = x;", "0x000Fh"),
        ("    if ( x > 0) { return x; }", "0x000Eh"),
        ("    return g( 'a', x);", "0x000Eh"),
        ("    return g(x,1);", "0x000Dh"),
        ("    return x ;", "0x000Ah"),
    ],
)
def test_errores_de_espaciado_reales_se_siguen_detectando(tmp_path: Path, linea: str, esperado: str):
    codigo = f"int g(char a, int b);\nint f(int x)\n{{\n{linea}\n}}\n"
    assert esperado in {cod for _, cod in _codigos(tmp_path, codigo)}


def test_mascara_opaca_preserva_columnas_y_lineas():
    texto = 'f("a\\"b", \'c\');\nx = "";\n'
    opaco = enmascarar_literales_opacos(texto)
    assert len(opaco) == len(texto)
    assert opaco.count("\n") == texto.count("\n")
    assert opaco.splitlines()[0] == "f(" + MARCA_LITERAL * 6 + ", " + MARCA_LITERAL * 3 + ");"
    assert opaco.splitlines()[1] == "x = " + MARCA_LITERAL * 2 + ";"
