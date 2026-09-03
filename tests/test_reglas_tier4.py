"""Tests unitarios para las 12 reglas de completitud (Tier 4) incorporadas a GAFF (total 100 reglas)."""

from pathlib import Path
import pytest
from gaff.core.linter import analizar_archivo, aplicar_autofix_archivo


def test_regla_0x0016h_colision_keywords(tmp_path: Path):
    src = tmp_path / "kw_col.c"
    src.write_text("void f(void) {\n    int bool = 1;\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x0016h"})
    assert len(viols) == 1
    assert viols[0].codigo == "0x0016h"
    assert "bool" in viols[0].mensaje


def test_regla_0x0017h_notacion_hungara(tmp_path: Path):
    src = tmp_path / "hungarian.c"
    src.write_text("void f(void) {\n    int int_edad = 20;\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x0017h"})
    assert len(viols) == 1
    assert viols[0].codigo == "0x0017h"
    assert "notación húngara" in viols[0].mensaje


def test_regla_0x100Eh_condicion_tautologica(tmp_path: Path):
    src = tmp_path / "taut.c"
    src.write_text("void f(void) {\n    if (1) {\n        return;\n    }\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x100Eh"})
    assert len(viols) == 1
    assert viols[0].codigo == "0x100Eh"
    assert "tautológica" in viols[0].mensaje


def test_regla_0x100Fh_for_condicion_compleja(tmp_path: Path):
    src = tmp_path / "for_comp.c"
    src.write_text("void f(int n, int fin) {\n    for (int i = 0; i < n && !fin; i++) {\n        continue;\n    }\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x100Fh"})
    assert len(viols) == 1
    assert viols[0].codigo == "0x100Fh"
    assert "condición de parada lógica compuesta" in viols[0].mensaje


def test_regla_0x200Eh_funcion_sin_void_y_autofix(tmp_path: Path):
    src = tmp_path / "no_void.c"
    src.write_text("void limpiar()\n{\n    return;\n}\n")
    # 1. Detección
    viols = analizar_archivo(src, reglas_habilitadas={"0x200Eh"})
    assert len(viols) == 1
    assert viols[0].codigo == "0x200Eh"
    assert viols[0].es_autofixable is True

    # 2. Autofix
    arreglos = aplicar_autofix_archivo(src)
    assert arreglos > 0

    # 3. Comprobar resultado
    res = src.read_text()
    assert "void limpiar(void)" in res


def test_regla_0x200Fh_auxiliar_sin_static(tmp_path: Path):
    hdr = tmp_path / "modulo.h"
    hdr.write_text("void funcion_publica(void);\n")
    src = tmp_path / "modulo.c"
    src.write_text('#include "modulo.h"\nvoid funcion_publica(void) {}\nint funcion_privada_olvidada(void) { return 0; }\n')
    viols = analizar_archivo(src, reglas_habilitadas={"0x200Fh"})
    assert len(viols) == 1
    assert viols[0].codigo == "0x200Fh"
    assert "funcion_privada_olvidada" in viols[0].mensaje


def test_regla_0x3016h_desreferencia_inmediata_malloc(tmp_path: Path):
    src = tmp_path / "deref_malloc.c"
    src.write_text("void f(void) {\n    int *p = malloc(sizeof(int));\n    *p = 10;\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x3016h"})
    assert len(viols) == 1
    assert viols[0].codigo == "0x3016h"
    assert "Desreferencia inmediata" in viols[0].mensaje


def test_regla_0x3017h_free_en_expresion(tmp_path: Path):
    src = tmp_path / "free_expr.c"
    src.write_text("void f(int *p) {\n    int x = (free(p), 0);\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x3017h"})
    assert len(viols) == 1
    assert viols[0].codigo == "0x3017h"
    assert "Uso de 'free()' en una expresión" in viols[0].mensaje


def test_regla_0x4008h_fclose_retorno_ignorado(tmp_path: Path):
    src = tmp_path / "fclose_ign.c"
    src.write_text('void f(void) {\n    FILE *arch = fopen("out.txt", "w");\n    if (!arch) return;\n    fclose(arch);\n}\n')
    viols = analizar_archivo(src, reglas_habilitadas={"0x4008h"})
    assert len(viols) == 1
    assert viols[0].codigo == "0x4008h"
    assert "Retorno de 'fclose(arch)' ignorado" in viols[0].mensaje


def test_regla_0x4009h_fopen_anidado(tmp_path: Path):
    src = tmp_path / "nested_fopen.c"
    src.write_text('void f(void) {\n    int x;\n    fscanf(fopen("data.txt", "r"), "%d", &x);\n}\n')
    viols = analizar_archivo(src, reglas_habilitadas={"0x4009h"})
    assert len(viols) == 1
    assert viols[0].codigo == "0x4009h"
    assert "Llamada anidada directa a 'fopen()'" in viols[0].mensaje


def test_regla_0x500Ch_include_archivo_c(tmp_path: Path):
    src = tmp_path / "inc_c.c"
    src.write_text('#include "modulo.c"\nint main(void) { return 0; }\n')
    viols = analizar_archivo(src, reglas_habilitadas={"0x500Ch"})
    assert len(viols) == 1
    assert viols[0].codigo == "0x500Ch"
    assert "Inclusión prohibida de archivo fuente C" in viols[0].mensaje


def test_regla_0x500Dh_redefinir_keyword(tmp_path: Path):
    src = tmp_path / "redef_kw.c"
    src.write_text('#define if while\nint main(void) { return 0; }\n')
    viols = analizar_archivo(src, reglas_habilitadas={"0x500Dh"})
    assert len(viols) == 1
    assert viols[0].codigo == "0x500Dh"
    assert "Redefinición prohibida de palabra clave" in viols[0].mensaje
