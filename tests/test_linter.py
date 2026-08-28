"""Tests unitarios para el motor de linting y autofix de GAFF."""

from pathlib import Path
import pytest
from gaff.core.linter import analizar_archivo, aplicar_autofix_archivo, ejecutar_linter


def test_detectar_goto(tmp_path):
    """Verifica la detección de la sentencia goto (GAFF008)."""
    fuente = tmp_path / "goto.c"
    fuente.write_text("""
    int main(void) {
        int x = 0;
        goto fin;
    fin:
        return 0;
    }
    """)
    viols = analizar_archivo(fuente)
    assert any(v.codigo == "GAFF008" for v in viols)


def test_detectar_guardas_faltantes(tmp_path):
    """Verifica detección de guardas de inclusión en .h (GAFF005)."""
    header = tmp_path / "lista.h"
    header.write_text("typedef struct nodo t_nodo;\n")
    viols = analizar_archivo(header)
    assert any(v.codigo == "GAFF005" for v in viols)


def test_autofix_keyword_spacing_y_guardas(tmp_path):
    """Verifica la aplicación de correcciones automáticas (GAFF005, GAFF007, GAFF010)."""
    header = tmp_path / "vector.h"
    header.write_text("void f(void){\n    if(1){\n        int x = 2;   \n    }\n}\n")

    arreglos = aplicar_autofix_archivo(header)
    assert arreglos > 0

    contenido_mod = header.read_text(encoding="utf-8")
    assert "if (" in contenido_mod
    assert "#ifndef VECTOR_H" in contenido_mod
    assert "#define VECTOR_H" in contenido_mod


def test_detectar_camel_case_en_funciones(tmp_path):
    """Verifica detección de camelCase en nombres de funciones (GAFF001)."""
    fuente = tmp_path / "camel.c"
    fuente.write_text("int calcularPromedio(int a, int b) { return a + b; }\n")
    viols = analizar_archivo(fuente)
    assert any(v.codigo == "GAFF001" for v in viols)


def test_archivo_limpio_sin_violaciones(tmp_path):
    """Verifica que un archivo correctamente estructurado pase sin violaciones."""
    fuente = tmp_path / "limpio.c"
    fuente.write_text("""#include <stdio.h>

int calcular_suma(int a, int b)
{
    if (a > 0)
    {
        return a + b;
    }
    return 0;
}
""")
    rep = ejecutar_linter([fuente])
    assert rep.ok is True
    assert rep.total_violaciones == 0
