"""Tests unitarios para las reglas del tier 3 incorporadas a GAFF."""

from pathlib import Path
import pytest
from gaff.core.linter import analizar_archivo


def test_regla_0x0014h_identificador_no_ascii(tmp_path: Path):
    src = tmp_path / "tildes.c"
    src.write_text("void f(void) {\n    int año = 2026;\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x0014h"})
    assert len(viols) == 1
    assert viols[0].codigo == "0x0014h"
    assert "año" in viols[0].mensaje


def test_regla_0x0015h_operador_coma_sentencias(tmp_path: Path):
    src = tmp_path / "coma.c"
    src.write_text("void f(void) {\n    int a = 0;\n    int b = 0;\n    a = 1, b = 2;\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x0015h"})
    assert len(viols) == 1
    assert viols[0].codigo == "0x0015h"
    assert "operador coma" in viols[0].mensaje


def test_regla_0x100Ch_switch_case_fallthrough(tmp_path: Path):
    src = tmp_path / "sw.c"
    src.write_text("void f(int op) {\n    switch (op) {\n    case 1:\n        printf(\"uno\");\n    case 2:\n        printf(\"dos\");\n        break;\n    default:\n        break;\n    }\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x100Ch"})
    assert len(viols) == 1
    assert viols[0].codigo == "0x100Ch"
    assert "sin sentencia 'break;'" in viols[0].mensaje


def test_regla_0x100Dh_modificar_contador_en_for(tmp_path: Path):
    src = tmp_path / "for_mod.c"
    src.write_text("void f(void) {\n    for (int i = 0; i < 10; i++) {\n        i += 2;\n    }\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x100Dh"})
    assert len(viols) == 1
    assert viols[0].codigo == "0x100Dh"
    assert "Modificación de la variable de iteración 'i'" in viols[0].mensaje


def test_regla_0x200Ch_retorno_direccion_stack(tmp_path: Path):
    src = tmp_path / "ret_local.c"
    src.write_text("int *f(void) {\n    int local = 10;\n    return &local;\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x200Ch"})
    assert len(viols) == 1
    assert viols[0].codigo == "0x200Ch"
    assert "Retorno de dirección de variable local '&local'" in viols[0].mensaje


def test_regla_0x3013h_sizeof_puntero_malloc(tmp_path: Path):
    src = tmp_path / "sz_ptr.c"
    src.write_text("void f(void) {\n    int *ptr = malloc(10 * sizeof(ptr));\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x3013h"})
    assert len(viols) == 1
    assert viols[0].codigo == "0x3013h"
    assert "Uso erróneo de 'sizeof(ptr)'" in viols[0].mensaje


def test_regla_0x3014h_double_free(tmp_path: Path):
    src = tmp_path / "df.c"
    src.write_text("void f(int *p) {\n    free(p);\n    free(p);\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x3014h"})
    assert len(viols) == 1
    assert viols[0].codigo == "0x3014h"
    assert "Doble liberación" in viols[0].mensaje


def test_regla_0x4006h_while_feof(tmp_path: Path):
    src = tmp_path / "feof_bad.c"
    src.write_text("void f(FILE *arch) {\n    char buf[10];\n    while (!feof(arch)) {\n        fgets(buf, 10, arch);\n    }\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x4006h"})
    assert len(viols) == 1
    assert viols[0].codigo == "0x4006h"
    assert "Antipatrón de lectura: 'while (!feof" in viols[0].mensaje


def test_regla_0x500Ah_macro_sin_parentesis(tmp_path: Path):
    src = tmp_path / "macro_noparen.c"
    src.write_text("#define MULT(a, b) a * b\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x500Ah"})
    assert len(viols) == 1
    assert viols[0].codigo == "0x500Ah"
    assert "no está protegido entre paréntesis" in viols[0].mensaje


def test_regla_0x500Bh_cabecera_estandar_faltante(tmp_path: Path):
    src = tmp_path / "missing_hdr.c"
    src.write_text("int main(void) {\n    printf(\"hola\");\n    return 0;\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x500Bh"})
    assert len(viols) == 1
    assert viols[0].codigo == "0x500Bh"
    assert "<stdio.h>" in viols[0].mensaje
