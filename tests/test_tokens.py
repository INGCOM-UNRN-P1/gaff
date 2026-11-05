"""Las reglas de espacios sobre los tokens de tree-sitter (ola R4)."""

import pytest

from gaff.core.linter import ejecutar_linter
from gaff.core.tokens import tokens_de

ESPACIOS = {"0x0003h", "0x000Ah", "0x000Bh", "0x000Ch", "0x000Dh", "0x000Eh", "0x000Fh", "0x0011h", "0x0016h"}


def _espacios(tmp_path, codigo):
    fuente = tmp_path / "prog.c"
    fuente.write_text(codigo, encoding="utf-8")
    reporte = ejecutar_linter([fuente], config={})
    return [(str(v.codigo), v.linea, v.columna) for a in reporte.archivos for v in a.violaciones
            if str(v.codigo) in ESPACIOS]


@pytest.mark.parametrize("linea", [
    'printf("a ,b ( c ) d  e =f %d", 1);',
    "char c = ',';",
    "char d = '(';",
    "double e = 1e-5;",
    "double f = 2.5e+3 + 1.0;",
    "return -1;",
    "int const *puntero = NULL;",
    "unsigned *iteraciones = NULL;",
    "char const *nombre = NULL;",
    "// a ,b ( c ) d  e =f",
    "/* a ,b ( c ) */",
])
def test_lo_que_no_es_un_error_de_espacios(tmp_path, linea):
    assert _espacios(tmp_path, f"#include <stdio.h>\nint f(void)\n{{\n    {linea}\n}}\n") == []


@pytest.mark.parametrize("codigo", [
    "int f(int a)\n{\n    return g(a,\n             a + 1\n    );\n}\n",
    "int f(int a)\n{\n    return a\n        * 2;\n}\n",
    "int f(int a)\n{\n    return (a +\n            1);\n}\n",
])
def test_las_continuaciones_de_linea_no_son_errores(tmp_path, codigo):
    assert _espacios(tmp_path, codigo) == []


@pytest.mark.parametrize("linea, codigo, columna", [
    ("x = a*b*c;", "0x0003h", 9),
    ("x = a-b-c;", "0x0003h", 9),
    ("x=1;", "0x0003h", 5),
    ("if(x) { }", "0x0003h", 5),
    ("x = f(a,b);", "0x000Dh", 12),
    ("x = f(a , b);", "0x000Ah", 12),
    ("x = f( a);", "0x000Eh", 10),
    ("x = f(a );", "0x000Eh", 12),
    ("x  = 1;", "0x000Fh", 6),
    ("x = n -> v;", "0x000Bh", 9),
    ("x ++;", "0x000Ch", 5),
    ("y = * p;", "0x0016h", 9),
])
def test_los_errores_de_espacios(tmp_path, linea, codigo, columna):
    hallazgos = _espacios(tmp_path, f"void g(void)\n{{\n    {linea}\n}}\n")

    assert (codigo, 3, columna) in hallazgos


def test_un_error_de_sintaxis_previo_no_vuelve_multiplicacion_a_un_declarador(tmp_path):
    assert ("0x0003h", 3, 1) not in _espacios(tmp_path, "int a = ;\n@\nint *f(void)\n{\n    return 0;\n}\n")


def test_la_columna_cuenta_caracteres_y_no_bytes(tmp_path):
    assert ("0x000Ah", 3, 23) in _espacios(tmp_path, 'void g(void)\n{\n    /* ñandú */ h("ñ") ;\n}\n')


def test_un_archivo_muy_anidado_no_agota_la_pila():
    codigo = "int a = " + "(" * 3000 + "1" + ")" * 3000 + ";\n"

    assert len(tokens_de(codigo, codigo.splitlines())) > 6000


def test_los_comentarios_y_el_preprocesador_no_son_tokens():
    codigo = "#define N  (1 ,2)\n// nada\nint x;\n"

    assert [t.texto for t in tokens_de(codigo, ["#define N  (1 ,2)", "", "int x;"])] == ["int", "x", ";"]
