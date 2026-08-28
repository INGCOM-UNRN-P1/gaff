"""Suite exhaustiva de pruebas para todas las verificaciones de reglas de cátedra en GAFF."""

import pytest
from pathlib import Path
from gaff.core.linter import analizar_archivo, aplicar_autofix_archivo, ejecutar_linter


def test_regla_0x0002h_multiples_declaraciones(tmp_path):
    fuente = tmp_path / "mult_decl.c"
    fuente.write_text("""
void test(void)
{
    int a, b = 10;
}
""")
    viols = analizar_archivo(fuente)
    assert any(v.codigo == "0x0002h" for v in viols)


def test_regla_0x0006h_asterisco_junto_a_tipo(tmp_path):
    fuente = tmp_path / "ptr_tipo.c"
    fuente.write_text("""
void test(void)
{
    int* ptr = NULL;
}
""")
    viols = analizar_archivo(fuente)
    assert any(v.codigo == "0x0006h" for v in viols)


def test_regla_0x0008h_constante_minusculas(tmp_path):
    fuente = tmp_path / "const_min.c"
    fuente.write_text("""
#define buffer_size 1024
""")
    viols = analizar_archivo(fuente)
    assert any(v.codigo == "0x0008h" for v in viols)


def test_regla_0x000Bh_llaves_en_misma_linea(tmp_path):
    fuente = tmp_path / "knr_style.c"
    fuente.write_text("""
void test(void) {
    if (1) {
        return;
    }
}
""")
    viols = analizar_archivo(fuente)
    assert any(v.codigo == "0x000Bh" for v in viols)


def test_regla_0x1001h_control_sin_llaves(tmp_path):
    fuente = tmp_path / "sin_llaves.c"
    fuente.write_text("""
void test(int x)
{
    if (x > 0)
        x++;
}
""")
    viols = analizar_archivo(fuente)
    assert any(v.codigo == "0x1001h" for v in viols)


def test_regla_0x1002h_continue(tmp_path):
    fuente = tmp_path / "continue.c"
    fuente.write_text("""
void test(void)
{
    for (int i = 0; i < 10; i++)
    {
        if (i == 2)
        {
            continue;
        }
    }
}
""")
    viols = analizar_archivo(fuente)
    assert any(v.codigo == "0x1002h" for v in viols)


def test_regla_0x1003h_for_indefinido(tmp_path):
    fuente = tmp_path / "for_indef.c"
    fuente.write_text("""
void test(void)
{
    for (;;)
    {
        break;
    }
}
""")
    viols = analizar_archivo(fuente)
    assert any(v.codigo == "0x1003h" for v in viols)


def test_regla_0x1007h_operador_ternario(tmp_path):
    fuente = tmp_path / "ternario.c"
    fuente.write_text("""
void test(int a, int b)
{
    int max = (a > b) ? a : b;
}
""")
    viols = analizar_archivo(fuente)
    assert any(v.codigo == "0x1007h" for v in viols)


def test_regla_0x1008h_switch_sin_default(tmp_path):
    fuente = tmp_path / "no_default.c"
    fuente.write_text("""
void test(int x)
{
    switch (x)
    {
        case 1:
            break;
    }
}
""")
    viols = analizar_archivo(fuente)
    assert any(v.codigo == "0x1008h" for v in viols)


def test_regla_0x2002h_printf_en_auxiliar(tmp_path):
    fuente = tmp_path / "calc.c"
    fuente.write_text("""
int calcular_raiz(int n)
{
    printf("Calculando...\n");
    return n;
}
""")
    viols = analizar_archivo(fuente)
    assert any(v.codigo == "0x2002h" for v in viols)


def test_regla_0x2004h_variable_global(tmp_path):
    fuente = tmp_path / "global.c"
    fuente.write_text("""
int contador_compartido = 0;

int main(void)
{
    return 0;
}
""")
    viols = analizar_archivo(fuente)
    assert any(v.codigo == "0x2004h" for v in viols)


def test_regla_0x3003h_asignacion_en_condicional(tmp_path):
    fuente = tmp_path / "asig_comp.c"
    fuente.write_text("""
void test(void)
{
    int *p;
    if ((p = malloc(10)) == NULL)
    {
        return;
    }
}
""")
    viols = analizar_archivo(fuente)
    assert any(v.codigo == "0x3003h" for v in viols)


def test_regla_0x3005h_puntero_triple(tmp_path):
    fuente = tmp_path / "triple_ptr.c"
    fuente.write_text("""
void test(int ***ptr_datos)
{
}
""")
    viols = analizar_archivo(fuente)
    assert any(v.codigo == "0x3005h" for v in viols)


def test_regla_0x300Bh_malloc_sin_sizeof(tmp_path):
    fuente = tmp_path / "malloc_raw.c"
    fuente.write_text("""
void test(void)
{
    int *p = malloc(100);
}
""")
    viols = analizar_archivo(fuente)
    assert any(v.codigo == "0x300Bh" for v in viols)


def test_regla_0x3008h_ptr_comparado_con_cero(tmp_path):
    fuente = tmp_path / "ptr_zero.c"
    fuente.write_text("""
void test(int *mi_ptr)
{
    if (mi_ptr == 0)
    {
        return;
    }
}
""")
    viols = analizar_archivo(fuente)
    assert any(v.codigo == "0x3008h" for v in viols)


def test_regla_0x0035h_struct_no_opaco_en_header(tmp_path):
    header = tmp_path / "tda.h"
    header.write_text("""
#ifndef TDA_H
#define TDA_H

struct nodo
{
    int valor;
};

#endif
""")
    viols = analizar_archivo(header)
    assert any(v.codigo == "0x0035h" for v in viols)


def test_regla_0x5001h_vla(tmp_path):
    fuente = tmp_path / "vla.c"
    fuente.write_text("""
void test(int n)
{
    int vector[n];
}
""")
    viols = analizar_archivo(fuente)
    assert any(v.codigo == "0x5001h" for v in viols)


def test_regla_0x5004h_strcpy(tmp_path):
    fuente = tmp_path / "strcpy.c"
    fuente.write_text("""
void test(char *dest, const char *src)
{
    strcpy(dest, src);
}
""")
    viols = analizar_archivo(fuente)
    assert any(v.codigo == "0x5004h" for v in viols)


def test_regla_0x5006h_gets_y_scanf_s(tmp_path):
    fuente = tmp_path / "inseguro.c"
    fuente.write_text("""
void test(char *buf)
{
    gets(buf);
    scanf("%s", buf);
}
""")
    viols = analizar_archivo(fuente)
    assert any(v.codigo == "0x5006h" for v in viols)


def test_autofix_pointer_asterisk(tmp_path):
    fuente = tmp_path / "ptr_fix.c"
    fuente.write_text("""
void test(void)
{
    int* ptr = NULL;
    char* str = NULL;
}
""")
    n = aplicar_autofix_archivo(fuente)
    assert n >= 2
    res = fuente.read_text(encoding="utf-8")
    assert "int *ptr" in res
    assert "char *str" in res


def test_regla_0x000Ch_nombre_archivo_con_espacios_y_mayusculas(tmp_path):
    fuente_espacios = tmp_path / "mi archivo fuente.c"
    fuente_espacios.write_text("int main(void)\n{\n    return 0;\n}\n")
    viols = analizar_archivo(fuente_espacios)
    assert any(v.codigo == "0x000Ch" for v in viols)

    fuente_camel = tmp_path / "CalculadoraAvanzada.c"
    fuente_camel.write_text("int main(void)\n{\n    return 0;\n}\n")
    viols_camel = analizar_archivo(fuente_camel)
    assert any(v.codigo == "0x000Ch" for v in viols_camel)

def test_autofix_allman_braces_style(tmp_path):
    fuente = tmp_path / "knr_fix.c"
    fuente.write_text("""
int sumar(int a, int b) {
    if (a > 0) {
        return a + b;
    } else {
        return 0;
    }
}
""")
    # Antes del fix tiene violaciones de Allman
    viols_antes = analizar_archivo(fuente)
    assert any(v.codigo == "0x000Bh" for v in viols_antes)

    # Aplicar autofix
    n = aplicar_autofix_archivo(fuente)
    assert n > 0

    # Después del fix las llaves están en líneas independientes estilo Allman
    res = fuente.read_text(encoding="utf-8")
    assert "int sumar(int a, int b)\n{" in res
    assert "if (a > 0)\n    {" in res or "if (a > 0)\n{" in res
    assert "else\n    {" in res or "else\n{" in res

    viols_despues = analizar_archivo(fuente)
    assert not any(v.codigo == "0x000Bh" for v in viols_despues)


