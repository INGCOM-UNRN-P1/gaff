"""Tests unitarios para las 10 reglas ampliadas de arquitectura y calidad de código en GAFF."""

from pathlib import Path
import pytest
from gaff.core.linter import analizar_archivo, aplicar_autofix_archivo


def test_regla_0x0013h_macro_en_minusculas(tmp_path: Path):
    src = tmp_path / "macro.c"
    src.write_text("#define buffer_max 1024\nint main(void) { return 0; }\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x0013h"})
    assert len(viols) == 1
    assert viols[0].codigo == "0x0013h"
    assert "buffer_max" in viols[0].mensaje


def test_regla_0x100Ah_asignacion_en_condicion(tmp_path: Path):
    src = tmp_path / "assign.c"
    src.write_text("void test(int x) {\n    if (x = 5) {\n        return;\n    }\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x100Ah"})
    assert len(viols) == 1
    assert viols[0].codigo == "0x100Ah"
    assert "Asignación simple" in viols[0].mensaje


def test_regla_0x100Bh_cuerpo_vacio_if(tmp_path: Path):
    src = tmp_path / "empty_if.c"
    src.write_text("void test(int x) {\n    if (x > 0);\n    {\n        return;\n    }\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x100Bh"})
    assert len(viols) == 1
    assert viols[0].codigo == "0x100Bh"
    assert "cuerpo nulo" in viols[0].mensaje


def test_regla_0x200Bh_demasiados_parametros(tmp_path: Path):
    src = tmp_path / "many_params.c"
    src.write_text("void crear_usuario(const char *nom, const char *ape, int edad, int dni, const char *mail) {\n    return;\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x200Bh"})
    assert len(viols) == 1
    assert viols[0].codigo == "0x200Bh"
    assert "recibe 5 parámetros" in viols[0].mensaje


def test_regla_0x3012h_aritmetica_void_ptr(tmp_path: Path):
    src = tmp_path / "void_arith.c"
    src.write_text("void test(void) {\n    void *p = malloc(10);\n    p++;\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x3012h"})
    assert len(viols) == 1
    assert viols[0].codigo == "0x3012h"
    assert "Aritmética de punteros sobre 'void *p'" in viols[0].mensaje


def test_regla_0x3015h_realloc_inseguro(tmp_path: Path):
    src = tmp_path / "unsafe_realloc.c"
    src.write_text("void test(int *buffer) {\n    buffer = realloc(buffer, 100);\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x3015h"})
    assert len(viols) == 1
    assert viols[0].codigo == "0x3015h"
    assert "Reasignación insegura con realloc" in viols[0].mensaje


def test_regla_0x4007h_ruta_absoluta_fopen(tmp_path: Path):
    src = tmp_path / "abs_path.c"
    src.write_text('void test(void) {\n    FILE *f = fopen("/home/usuario/datos.txt", "r");\n}\n')
    viols = analizar_archivo(src, reglas_habilitadas={"0x4007h"})
    assert len(viols) == 1
    assert viols[0].codigo == "0x4007h"
    assert "Ruta absoluta hardcodeada" in viols[0].mensaje


def test_regla_0x5007h_inclusiones_duplicadas_y_autofix(tmp_path: Path):
    src = tmp_path / "dup_inc.c"
    src.write_text("#include <stdio.h>\n#include <stdlib.h>\n#include <stdio.h>\nint main(void) { return 0; }\n")
    # 1. Detección
    viols = analizar_archivo(src, reglas_habilitadas={"0x5007h"})
    assert len(viols) == 1
    assert viols[0].codigo == "0x5007h"
    assert viols[0].es_autofixable is True

    # 2. Autofix
    arreglos = aplicar_autofix_archivo(src)
    assert arreglos > 0

    # 3. Verificación de contenido deduplicado
    contenido = src.read_text()
    assert contenido.count("#include <stdio.h>") == 1

    # 4. Sin violaciones posteriores
    viols_post = analizar_archivo(src, reglas_habilitadas={"0x5007h"})
    assert len(viols_post) == 0


def test_regla_0x5008h_funciones_obsoletas(tmp_path: Path):
    src = tmp_path / "obsoletas.c"
    src.write_text("void test(char *s) {\n    char buf[10];\n    gets(buf);\n    int n = atoi(s);\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x5008h"})
    assert len(viols) == 2
    assert any("gets" in v.mensaje for v in viols)
    assert any("atoi" in v.mensaje for v in viols)


def test_regla_0x5009h_division_entera_flotante(tmp_path: Path):
    src = tmp_path / "float_div.c"
    src.write_text("void test(void) {\n    float f = 1 / 2;\n    double d = 3 / 4;\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x5009h"})
    assert len(viols) == 2
    assert viols[0].codigo == "0x5009h"
    assert viols[1].codigo == "0x5009h"
