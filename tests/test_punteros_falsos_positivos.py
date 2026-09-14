"""Tests para verificar la eliminación de falsos positivos en reglas de punteros (* y &)."""

from pathlib import Path
from gaff.core.linter import analizar_archivo


def test_regla_0x3008h_no_falso_positivo_en_desreferencia(tmp_path: Path):
    """Verifica que *ptr == 0 o *buffer != 0 no disparen 0x3008h."""
    src = tmp_path / "deref_zero.c"
    src.write_text("""
/* Comentario */
#include <stdbool.h>

void test_fn(int *ptr, char *buffer) {
    if (*ptr == 0) {
        return;
    }
    if (*buffer != 0) {
        return;
    }
}
""")
    viols = analizar_archivo(src, reglas_habilitadas={"0x3008h"})
    assert len(viols) == 0, f"Falso positivo en 0x3008h: {[v.mensaje for v in viols]}"

    # Verificar que ptr == 0 legítimo SÍ se detecte
    src_bad = tmp_path / "bad_ptr_zero.c"
    src_bad.write_text("""
/* Comentario */
void test_fn(int *ptr) {
    if (ptr == 0) {
        return;
    }
}
""")
    viols_bad = analizar_archivo(src_bad, reglas_habilitadas={"0x3008h"})
    assert any(v.codigo == "0x3008h" for v in viols_bad)


def test_regla_0x3019h_no_falso_positivo_en_desreferencia(tmp_path: Path):
    """Verifica que *ptr == 5 o *ptr > 10 no disparen 0x3019h."""
    src = tmp_path / "deref_num.c"
    src.write_text("""
/* Comentario */
void test_fn(int *ptr) {
    if (*ptr == 5) {
        return;
    }
    if (*ptr > 10) {
        return;
    }
    if (*ptr != 1) {
        return;
    }
}
""")
    viols = analizar_archivo(src, reglas_habilitadas={"0x3019h"})
    assert len(viols) == 0, f"Falso positivo en 0x3019h: {[v.mensaje for v in viols]}"

    # Verificar que ptr == 5 legítimo SÍ se detecte
    src_bad = tmp_path / "bad_ptr_cmp.c"
    src_bad.write_text("""
/* Comentario */
void test_fn(int *ptr) {
    if (ptr == 5) {
        return;
    }
}
""")
    viols_bad = analizar_archivo(src_bad, reglas_habilitadas={"0x3019h"})
    assert any(v.codigo == "0x3019h" for v in viols_bad)


def test_regla_0x0003h_no_falso_positivo_en_declaracion_struct_ptr(tmp_path: Path):
    """Verifica que 'Persona *p = &x;' no se interprete como multiplicación sin espacios."""
    src = tmp_path / "struct_ptr.c"
    src.write_text("""
/* Comentario */
typedef struct Persona {
    int edad;
} Persona;

void test_fn(void) {
    Persona persona_local = {0};
    Persona *ptr_persona = &persona_local;
    struct Persona *ptr_struct = &persona_local;
}
""")
    viols = analizar_archivo(src, reglas_habilitadas={"0x0003h"})
    mensajes_mul = [v.mensaje for v in viols if "operador binario '*'" in v.mensaje]
    assert len(mensajes_mul) == 0, f"Falso positivo en 0x0003h: {mensajes_mul}"


def test_regla_0x0016h_expresiones_mixtas_punteros_y_direcciones(tmp_path: Path):
    """Verifica que operaciones unarias válidas con * y & no disparen 0x0016h."""
    src = tmp_path / "unary_valid.c"
    src.write_text("""
/* Comentario */
void test_fn(int *p, int mask, int x) {
    int val = *p & mask;
    int *dest = &x;
    int *cast_ptr = (int *) &x;
    *p = &x ? *p : 0;
}
""")
    viols = analizar_archivo(src, reglas_habilitadas={"0x0016h"})
    assert len(viols) == 0, f"Falso positivo en 0x0016h: {[v.mensaje for v in viols]}"

    # Verificar que & x (con espacio indebido) SÍ se detecte
    src_bad = tmp_path / "unary_bad.c"
    src_bad.write_text("""
/* Comentario */
void test_fn(int *p, int x) {
    int *dest = & x;
}
""")
    viols_bad = analizar_archivo(src_bad, reglas_habilitadas={"0x0016h"})
    assert any(v.codigo == "0x0016h" for v in viols_bad)
