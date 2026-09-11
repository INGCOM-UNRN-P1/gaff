"""Tests para las mejoras QoL implementadas de GAFF (0x0020h, 0x5016h, 0x1014h)."""

from pathlib import Path
from gaff.core.linter import analizar_archivo


def test_qol_proportionality_0x0020h(tmp_path: Path):
    """0x0020h: Identificadores breves no descriptivos en alcance de archivo."""
    src_bad = tmp_path / "bad_prop.c"
    src_bad.write_text(
        "int x = 10;\n"
        "int f(void)\n"
        "{\n"
        "    return x;\n"
        "}\n"
    )
    viols = analizar_archivo(src_bad, reglas_habilitadas={"0x0020h"})
    assert any(v.codigo == "0x0020h" and "f" in v.mensaje for v in viols)
    assert any(v.codigo == "0x0020h" and "x" in v.mensaje for v in viols)

    src_ok = tmp_path / "ok_prop.c"
    src_ok.write_text(
        "int contador_global = 10;\n"
        "int procesar_datos(void)\n"
        "{\n"
        "    int i = 0;\n"
        "    return contador_global + i;\n"
        "}\n"
    )
    viols_ok = analizar_archivo(src_ok, reglas_habilitadas={"0x0020h"})
    assert not any(v.codigo == "0x0020h" for v in viols_ok)


def test_qol_std_headers_0x5016h(tmp_path: Path):
    """0x5016h: Funciones de libc sin incluir su cabecera estándar."""
    src_bad = tmp_path / "bad_hdr.c"
    src_bad.write_text(
        "int main(void)\n"
        "{\n"
        "    char *p = malloc(10);\n"
        "    printf(\"hola\");\n"
        "    return 0;\n"
        "}\n"
    )
    viols = analizar_archivo(src_bad, reglas_habilitadas={"0x5016h"})
    assert any(v.codigo == "0x5016h" and "malloc" in v.mensaje and "stdlib.h" in v.mensaje for v in viols)
    assert any(v.codigo == "0x5016h" and "printf" in v.mensaje and "stdio.h" in v.mensaje for v in viols)

    src_ok = tmp_path / "ok_hdr.c"
    src_ok.write_text(
        "#include <stdio.h>\n"
        "#include <stdlib.h>\n"
        "int main(void)\n"
        "{\n"
        "    char *p = malloc(10);\n"
        "    printf(\"hola\");\n"
        "    free(p);\n"
        "    return 0;\n"
        "}\n"
    )
    viols_ok = analizar_archivo(src_ok, reglas_habilitadas={"0x5016h"})
    assert not any(v.codigo == "0x5016h" for v in viols_ok)


def test_qol_ctrl_assign_0x1014h(tmp_path: Path):
    """0x1014h: Asignaciones embebidas dentro de estructuras de control."""
    src_bad = tmp_path / "bad_assign.c"
    src_bad.write_text(
        "int main(void)\n"
        "{\n"
        "    int c = 0;\n"
        "    while ((c = 5) != 0)\n"
        "    {\n"
        "        break;\n"
        "    }\n"
        "    return 0;\n"
        "}\n"
    )
    viols = analizar_archivo(src_bad, reglas_habilitadas={"0x1014h"})
    assert any(v.codigo == "0x1014h" and "c" in v.mensaje and "while" in v.mensaje for v in viols)

    src_ok = tmp_path / "ok_assign.c"
    src_ok.write_text(
        "int main(void)\n"
        "{\n"
        "    int c = 5;\n"
        "    while (c != 0)\n"
        "    {\n"
        "        c = 0;\n"
        "    }\n"
        "    return 0;\n"
        "}\n"
    )
    viols_ok = analizar_archivo(src_ok, reglas_habilitadas={"0x1014h"})
    assert not any(v.codigo == "0x1014h" for v in viols_ok)
