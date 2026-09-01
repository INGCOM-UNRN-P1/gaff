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

def test_catalogo_reglas_adicionales_catedra():
    """Verifica el alta de las reglas de cátedra 0x300Dh, 0x1007h, 0x3004h, 0x5003h, 0x2001h, 0x000Dh."""
    from gaff.core.rules import CATALOGO_REGLAS, obtener_regla

    for cod in ("0x300Dh", "0x1007h", "0x3004h", "0x5003h", "0x2001h", "0x000Dh"):
        assert cod in CATALOGO_REGLAS
        assert obtener_regla(cod)["titulo"]


def test_regla_gaff061_numero_magico(tmp_path):
    fuente = tmp_path / "magic.c"
    fuente.write_text("""
void test(void)
{
    for (int i = 0; i < 5; i++)
    {
        int x = i * 3;
    }
}
""")
    viols = analizar_archivo(fuente, reglas_habilitadas={"0x300Dh"})
    magicos = [v for v in viols if v.codigo == "0x300Dh"]
    assert len(magicos) == 2
    assert any("'5'" in v.mensaje for v in magicos)
    assert any("'3'" in v.mensaje for v in magicos)


def test_regla_gaff061_no_flag_en_define_enum_y_valores_comunes(tmp_path):
    fuente = tmp_path / "ok_magic.c"
    fuente.write_text("""
#define MAX_INTENTOS 5
typedef enum { OK = 0, ERROR = 3 } estado_t;

int main(void)
{
    printf("Error 404 en registro\\n");
    return 0;
}
""")
    viols = analizar_archivo(fuente, reglas_habilitadas={"0x300Dh"})
    assert viols == []


def test_regla_gaff062_alias_ternario(tmp_path):
    fuente = tmp_path / "tern.c"
    fuente.write_text("""
int maximo(int a, int b)
{
    return (a > b) ? a : b;
}
""")
    viols = analizar_archivo(fuente, reglas_habilitadas={"0x1007h"})
    assert any(v.codigo == "0x1007h" for v in viols)


def test_regla_gaff063_alias_typedef(tmp_path):
    header = tmp_path / "tipos_dato.h"
    header.write_text("""
#ifndef TIPOS_DATO_H
#define TIPOS_DATO_H

typedef struct nodo Nodo;

#endif
""")
    viols = analizar_archivo(header, reglas_habilitadas={"0x3004h"})
    assert any(v.codigo == "0x3004h" for v in viols)


def test_regla_gaff064_alias_guardas(tmp_path):
    header = tmp_path / "sin_guarda.h"
    header.write_text("void funcion(void);\n")
    viols = analizar_archivo(header, reglas_habilitadas={"0x5003h"})
    assert any(v.codigo == "0x5003h" for v in viols)


def test_regla_gaff065_anidacion_profunda(tmp_path):
    fuente = tmp_path / "flecha.c"
    fuente.write_text("""
void proceso(int a, int b, int c, int d)
{
    if (a > 0)
    {
        if (b > 0)
        {
            if (c > 0)
            {
                if (d > 0)
                {
                    a++;
                }
            }
        }
    }
}
""")
    viols = analizar_archivo(fuente, reglas_habilitadas={"0x2001h"})
    assert any(v.codigo == "0x2001h" for v in viols)


def test_regla_gaff065_anidacion_tres_niveles_permitida(tmp_path):
    fuente = tmp_path / "tres_niveles.c"
    fuente.write_text("""
void proceso(int a, int b, int c)
{
    if (a > 0)
    {
        if (b > 0)
        {
            if (c > 0)
            {
                a++;
            }
        }
    }
}
""")
    viols = analizar_archivo(fuente, reglas_habilitadas={"0x2001h"})
    assert viols == []


def test_regla_gaff066_codigo_comentado(tmp_path):
    fuente = tmp_path / "muerto.c"
    fuente.write_text("""
int main(void)
{
    // int resultado_viejo = calcular(2);
    int resultado = calcular(2);
    /*
    if (resultado < 0)
    {
        return 0;
    }
    */
    return resultado;
}
""")
    viols = analizar_archivo(fuente, reglas_habilitadas={"0x000Dh"})
    assert sum(1 for v in viols if v.codigo == "0x000Dh") == 2


def test_regla_gaff066_comentario_doxygen_permitido(tmp_path):
    fuente = tmp_path / "doc.c"
    fuente.write_text("""
/**
 * @brief Suma dos enteros.
 * @param a Primer sumando.
 * @return Resultado de la suma.
 */
int sumar(int a, int b)
{
    return a + b;
}
""")
    viols = analizar_archivo(fuente, reglas_habilitadas={"0x000Dh"})
    assert viols == []


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


def test_sincronizacion_apunte_reglas():
    """Verifica que GAFF cargue y sincronice las 60 reglas canónicas de p1-apunte/reglas."""
    from gaff.core.rules import CATALOGO_REGLAS, cargar_reglas_desde_apunte, obtener_regla

    reglas = cargar_reglas_desde_apunte()
    assert len(reglas) >= 60

    # Verificar presencia de reglas representativas de cada categoría
    assert "0x0001h" in CATALOGO_REGLAS
    assert "0x1002h" in CATALOGO_REGLAS
    assert "0x2001h" in CATALOGO_REGLAS
    assert "0x300Dh" in CATALOGO_REGLAS
    assert "0x4001h" in CATALOGO_REGLAS
    assert "0x5003h" in CATALOGO_REGLAS

    # Verificar coincidencia de títulos con p1-apunte/reglas
    r_0x0001 = obtener_regla("0x0001h")
    assert r_0x0001 is not None
    assert r_0x0001["titulo"] == "Los identificadores deben ser descriptivos"

    r_0x1002 = obtener_regla("0x1002h")
    assert r_0x1002 is not None
    assert "break y continue" in r_0x1002["titulo"]

    r_0x300d = obtener_regla("0x300Dh")
    assert r_0x300d is not None
    assert "números mágicos" in r_0x300d["titulo"].lower()



