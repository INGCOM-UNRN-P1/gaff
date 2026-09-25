"""Tests para las mejoras QoL de GAFF (directiva gaff:ignore, catálogo MyST y reglas 0x0022h..0x301Ah)."""

from pathlib import Path
from typer.testing import CliRunner

from gaff.cli import app
from gaff.core.linter import analizar_archivo, aplicar_autofix_archivo

runner = CliRunner()


def test_gaff_ignore_directive(tmp_path: Path):
    src = tmp_path / "test_ignore.c"
    # Línea 4 con justificación válida -> suprime 0x0001h
    # Línea 6 sin justificación -> NO suprime
    src.write_text(
        "/*\n * Cátedra de Programación 1\n */\n"
        "int a = 1; // gaff:ignore 0x0001h excepción autorizada por consigna docente\n"
        "int b = 2;\n"
        "int m = 3; // gaff:ignore 0x0001h\n"
    )
    viols = analizar_archivo(src, reglas_habilitadas={"0x0001h"})
    # 'a' debe estar suprimida
    assert not any(v.linea == 4 and "a" in v.mensaje for v in viols)
    # 'm' debe estar reportada porque la directiva carece de justificación
    assert any(v.linea == 6 and "m" in v.mensaje for v in viols)


def test_qol_control_spacing_0x0022h(tmp_path: Path):
    src = tmp_path / "ctrl_space.c"
    src.write_text("/* Cátedra */\nint main(void) {\n    if(1) {\n        return 0;\n    }\n    return 1;\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x0022h"})
    assert any(v.codigo == "0x0022h" and "if" in v.mensaje for v in viols)

    # Probar autofix
    aplicar_autofix_archivo(src)
    assert "if (" in src.read_text(encoding="utf-8")


def test_qol_const_uninit_0x0023h(tmp_path: Path):
    src = tmp_path / "const_uninit.c"
    src.write_text("/* Cátedra */\nint main(void) {\n    const int x;\n    const int y = 10;\n    return y;\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x0023h"})
    assert any(v.codigo == "0x0023h" and "x" in v.mensaje for v in viols)
    assert not any(v.codigo == "0x0023h" and "y" in v.mensaje for v in viols)


def test_qol_fn_ptr_format_0x0025h(tmp_path: Path):
    src = tmp_path / "fn_ptr.c"
    src.write_text("/* Cátedra */\ntypedef int (* operacion_t )(int, int);\ntypedef int (*valida_t)(int, int);\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x0025h"})
    assert any(v.codigo == "0x0025h" and "operacion_t" in v.mensaje for v in viols)
    assert not any(v.codigo == "0x0025h" and "valida_t" in v.mensaje for v in viols)


def test_qol_reserved_identifiers_0x0026h(tmp_path: Path):
    src = tmp_path / "reserved.c"
    src.write_text("/* Cátedra */\nint __privado = 10;\nint _Mayus = 20;\nint variable_ok = 30;\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x0026h"})
    assert any(v.codigo == "0x0026h" and "__privado" in v.mensaje for v in viols)
    assert any(v.codigo == "0x0026h" and "_Mayus" in v.mensaje for v in viols)
    assert not any(v.codigo == "0x0026h" and "variable_ok" in v.mensaje for v in viols)


def test_qol_header_documentation_0x0027h(tmp_path: Path):
    src_bad = tmp_path / "sin_doc.c"
    src_bad.write_text(
        "int f(void) { return 0; }\n"
        "int g(void) { return 1; }\n"
        "int h(void) { return 2; }\n"
        "int i(void) { return 3; }\n"
        "int j(void) { return 4; }\n"
        "int k(void) { return 5; }\n"
        "int l(void) { return 6; }\n"
        "int m(void) { return 7; }\n"
        "int n(void) { return 8; }\n"
        "int main(void) { return 0; }\n"
    )
    viols_bad = analizar_archivo(src_bad, reglas_habilitadas={"0x0027h"})
    assert any(v.codigo == "0x0027h" for v in viols_bad)

    src_ok = tmp_path / "con_doc.c"
    src_ok.write_text("/*\n * Cátedra de Programación 1\n * Módulo de pruebas\n */\nint f(void) { return 0; }\n")
    viols_ok = analizar_archivo(src_ok, reglas_habilitadas={"0x0027h"})
    assert not any(v.codigo == "0x0027h" for v in viols_ok)


def test_qol_goto_label_alignment_0x0028h(tmp_path: Path):
    src = tmp_path / "label_align.c"
    src.write_text("/* Cátedra */\nvoid test(void) {\n    cleanup:\n        return;\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x0028h"})
    assert any(v.codigo == "0x0028h" and "cleanup" in v.mensaje for v in viols)


def test_qol_array_overflow_0x0029h(tmp_path: Path):
    src = tmp_path / "arr_over.c"
    src.write_text("/* Cátedra */\nvoid test(void) {\n    int vec[3] = {1, 2, 3, 4};\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x0029h"})
    assert any(v.codigo == "0x0029h" and "vec" in v.mensaje for v in viols)


def test_qol_args_spacing_and_autofix_0x002Bh(tmp_path: Path):
    src = tmp_path / "args_comma.c"
    src.write_text("/* Cátedra */\nvoid test(void) {\n    calcular(1,2,3);\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x002Bh"})
    assert any(v.codigo == "0x002Bh" for v in viols)

    aplicar_autofix_archivo(src)
    assert "calcular(1, 2, 3);" in src.read_text(encoding="utf-8")


def test_qol_macro_case_0x002Ch(tmp_path: Path):
    src = tmp_path / "macro_case.c"
    src.write_text("/* Cátedra */\n#define max_size 100\n#define BUFFER_OK 200\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x002Ch"})
    assert any(v.codigo == "0x002Ch" and "max_size" in v.mensaje for v in viols)
    assert not any(v.codigo == "0x002Ch" and "BUFFER_OK" in v.mensaje for v in viols)


def test_qol_unary_spacing_0x002Dh(tmp_path: Path):
    src = tmp_path / "unary.c"
    src.write_text("/* Cátedra */\nvoid test(int *p) {\n    int x = * p;\n    ++ x;\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x002Dh"})
    assert any(v.codigo == "0x002Dh" for v in viols)


def test_qol_complex_logic_parens_0x1016h(tmp_path: Path):
    src = tmp_path / "complex_logic.c"
    src.write_text("/* Cátedra */\nvoid test(int a, int b, int c) {\n    if (a && b || c) return;\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x1016h"})
    assert any(v.codigo == "0x1016h" for v in viols)


def test_qol_multi_increment_0x1017h(tmp_path: Path):
    src = tmp_path / "multi_inc.c"
    src.write_text("/* Cátedra */\nvoid test(int i) {\n    int x = i++ + ++i;\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x1017h"})
    assert any(v.codigo == "0x1017h" and "i" in v.mensaje for v in viols)


def test_qol_superfluous_else_0x2016h(tmp_path: Path):
    src = tmp_path / "superfluous_else.c"
    src.write_text(
        "/* Cátedra */\nint test(int x) {\n"
        "    if (x < 0) {\n"
        "        return -1;\n"
        "    } else {\n"
        "        return x;\n"
        "    }\n"
        "}\n"
    )
    viols = analizar_archivo(src, reglas_habilitadas={"0x2016h"})
    assert any(v.codigo == "0x2016h" for v in viols)


def test_qol_idiomatic_bool_0x301Ah(tmp_path: Path):
    src = tmp_path / "bad_bool.c"
    src.write_text("/* Cátedra */\ntypedef int BOOLEAN;\n#define TRUE 1\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x301Ah"})
    assert any(v.codigo == "0x301Ah" for v in viols)


def test_catalogo_myst_generado():
    cat_dir = Path(__file__).resolve().parents[1] / "catalogo"
    assert (cat_dir / "index.md").is_file()
    assert (cat_dir / "0x0001h.md").is_file()
    assert (cat_dir / "0x0022h.md").is_file()
    contenido_index = (cat_dir / "index.md").read_text(encoding="utf-8")
    assert "0x0001h" in contenido_index
