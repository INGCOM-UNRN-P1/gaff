"""Tests unitarios para las reglas de espaciado intra-línea en GAFF."""

from pathlib import Path
import pytest
from gaff.core.linter import analizar_archivo, aplicar_autofix_archivo


def test_regla_0x0003h_operadores_binarios(tmp_path: Path):
    src = tmp_path / "bin_op.c"
    src.write_text("int f(int a, int b) {\n    int res=a+b;\n    if (res==10) return res;\n    return 0;\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x0003h"})
    assert len(viols) >= 2
    assert any("=" in v.mensaje for v in viols)
    assert any("+" in v.mensaje or "==" in v.mensaje for v in viols)


def test_regla_0x000Bh_miembros_struct_y_autofix(tmp_path: Path):
    src = tmp_path / "members.c"
    src.write_text("struct Punto\n{\n    int x;\n};\nvoid f(struct Punto *p, struct Punto s)\n{\n    int a = p -> x;\n    int b = s . x;\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x000Bh"})
    assert len(viols) == 2
    assert viols[0].codigo == "0x000Bh"
    assert viols[0].es_autofixable is True

    # Autofix
    arreglos = aplicar_autofix_archivo(src)
    assert arreglos > 0
    res = src.read_text()
    assert "p->x" in res
    assert "s.x" in res


def test_regla_0x000Ch_unarios_y_autofix(tmp_path: Path):
    src = tmp_path / "unarios.c"
    src.write_text("void f(int x) {\n    x ++;\n    ++ x;\n    if (! x) return;\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x000Ch"})
    assert len(viols) == 3
    assert viols[0].codigo == "0x000Ch"
    assert viols[0].es_autofixable is True

    # Autofix
    arreglos = aplicar_autofix_archivo(src)
    assert arreglos > 0
    res = src.read_text()
    assert "x++;" in res
    assert "++x;" in res
    assert "!x" in res


def test_regla_0x000Dh_espacio_tras_coma_y_autofix(tmp_path: Path):
    src = tmp_path / "comas.c"
    src.write_text("void f(int a,int b,int c)\n{\n    int x,y;\n    (void)x;\n    (void)y;\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x000Dh"})
    assert len(viols) >= 2
    assert viols[0].codigo == "0x000Dh"
    assert viols[0].es_autofixable is True

    # Autofix
    arreglos = aplicar_autofix_archivo(src)
    assert arreglos > 0
    res = src.read_text()
    assert "int a, int b, int c" in res
    assert "int x, y;" in res


def test_regla_0x000Eh_espacios_parentesis_y_autofix(tmp_path: Path):
    src = tmp_path / "parens.c"
    src.write_text("void f(int a)\n{\n    if ( a > 0 ) {\n        f( a );\n    }\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x000Eh"})
    assert len(viols) >= 2
    assert viols[0].codigo == "0x000Eh"
    assert viols[0].es_autofixable is True

    # Autofix
    arreglos = aplicar_autofix_archivo(src)
    assert arreglos > 0
    res = src.read_text()
    assert "if (a > 0)" in res
    assert "f(a);" in res


def test_regla_0x000Fh_espacios_multiples_y_autofix(tmp_path: Path):
    src = tmp_path / "multi_spaces.c"
    src.write_text("void f(void)\n{\n    int   total   =   10;\n    (void)total;\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x000Fh"})
    assert len(viols) >= 1
    assert viols[0].codigo == "0x000Fh"
    assert viols[0].es_autofixable is True

    # Autofix
    arreglos = aplicar_autofix_archivo(src)
    assert arreglos > 0
    res = src.read_text()
    assert "    int total = 10;" in res
