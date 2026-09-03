"""Tests unitarios para las 10 reglas del Tier 5 en GAFF (total 110 reglas)."""

from pathlib import Path
import pytest
from gaff.core.linter import analizar_archivo, aplicar_autofix_archivo


def test_regla_0x0018h_prefijos_reservados(tmp_path: Path):
    src = tmp_path / "res_pref.c"
    src.write_text("void f(void) {\n    int __reservado = 1;\n    int _Privado = 2;\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x0018h"})
    assert len(viols) == 2
    assert viols[0].codigo == "0x0018h"
    assert viols[1].codigo == "0x0018h"


def test_regla_0x0019h_espacios_separadores_y_autofix(tmp_path: Path):
    src = tmp_path / "espacios_sep.c"
    src.write_text("void f(void)\n{\n    int a , b = 10 ;\n}\n")
    # 1. Detección
    viols = analizar_archivo(src, reglas_habilitadas={"0x0019h"})
    assert len(viols) == 2
    assert viols[0].codigo == "0x0019h"
    assert viols[0].es_autofixable is True

    # 2. Autofix
    arreglos = aplicar_autofix_archivo(src)
    assert arreglos > 0

    # 3. Comprobar resultado sin espacios antes de coma o punto y coma
    res = src.read_text()
    assert "int a, b = 10;" in res


def test_regla_0x1010h_do_while_sin_llaves(tmp_path: Path):
    src = tmp_path / "do_no_braces.c"
    src.write_text("void f(int x) {\n    do x++; while (x < 10);\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x1010h"})
    assert len(viols) == 1
    assert viols[0].codigo == "0x1010h"
    assert "sin bloque de llaves" in viols[0].mensaje


def test_regla_0x1011h_else_tras_return(tmp_path: Path):
    src = tmp_path / "else_ret.c"
    src.write_text("int f(int x) {\n    if (x > 0) {\n        return 1;\n    } else {\n        return 0;\n    }\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x1011h"})
    assert len(viols) == 1
    assert viols[0].codigo == "0x1011h"
    assert "Cláusula 'else' redundante" in viols[0].mensaje


def test_regla_0x2010h_shadowing_parametro(tmp_path: Path):
    src = tmp_path / "shadow.c"
    src.write_text("void f(int cantidad) {\n    int cantidad = 5;\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x2010h"})
    assert len(viols) == 1
    assert viols[0].codigo == "0x2010h"
    assert "sombrea (shadows)" in viols[0].mensaje


def test_regla_0x2011h_mutar_parametro_valor(tmp_path: Path):
    src = tmp_path / "param_mut.c"
    src.write_text("int f(int limite) {\n    limite--;\n    return limite;\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x2011h"})
    assert len(viols) == 1
    assert viols[0].codigo == "0x2011h"
    assert "Modificación del parámetro recibido por valor" in viols[0].mensaje


def test_regla_0x3018h_free_const(tmp_path: Path):
    src = tmp_path / "free_const.c"
    src.write_text("void f(void) {\n    const char *fijo = \"texto\";\n    free((void *)fijo);\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x3018h"})
    assert len(viols) == 1
    assert viols[0].codigo == "0x3018h"
    assert "puntero constante" in viols[0].mensaje


def test_regla_0x3019h_ptr_comparado_con_entero(tmp_path: Path):
    src = tmp_path / "ptr_cmp_int.c"
    src.write_text("void f(int *ptr) {\n    if (ptr == 1) {\n        return;\n    }\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x3019h"})
    assert len(viols) == 1
    assert viols[0].codigo == "0x3019h"
    assert "Comparación ilegítima de puntero" in viols[0].mensaje


def test_regla_0x400Ah_use_after_close(tmp_path: Path):
    src = tmp_path / "uac.c"
    src.write_text('void f(void) {\n    FILE *arch = fopen("t.txt", "r");\n    fclose(arch);\n    fgetc(arch);\n}\n')
    viols = analizar_archivo(src, reglas_habilitadas={"0x400Ah"})
    assert len(viols) == 1
    assert viols[0].codigo == "0x400Ah"
    assert "use-after-close" in viols[0].mensaje


def test_regla_0x500Eh_conio_h(tmp_path: Path):
    src = tmp_path / "conio_test.c"
    src.write_text('#include <conio.h>\nint main(void) {\n    getch();\n    return 0;\n}\n')
    viols = analizar_archivo(src, reglas_habilitadas={"0x500Eh"})
    assert len(viols) >= 1
    assert any(v.codigo == "0x500Eh" for v in viols)
