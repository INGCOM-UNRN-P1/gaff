"""Tests de verificación exhaustiva del análisis de estilo en GAFF:
- Números mágicos (enteros, decimales, hex, const permitido, define/enum permitido, -1 unario)
- Identificadores cortos no descriptivos (1 letra no canónica, abreviaciones crípticas)
- Identificadores largos (> 31 caracteres estándar ISO C)
- Identificadores en camelCase (variables locales, parámetros y lazos)
- Variables no inicializadas a un valor conocido
"""

from pathlib import Path
from gaff.core.linter import analizar_archivo


def test_gaff_identificadores_una_letra_no_descriptiva(tmp_path: Path):
    """Regla 0x0001h (GAFF011): variables de una sola letra no canónicas."""
    fuente = tmp_path / "una_letra.c"
    fuente.write_text("""
int procesar(int d)
{
    int p = 10;
    int a = 5;
    for (int q = 0; q < 5; q++)
    {
        p += q;
    }
    return p;
}
""")
    viols = analizar_archivo(fuente, reglas_habilitadas={"0x0001h"})
    mensajes = [v.mensaje for v in viols if v.codigo == "0x0001h"]
    assert any("'p'" in m for m in mensajes)
    assert any("'a'" in m for m in mensajes)
    assert any("'d'" in m for m in mensajes)
    assert any("'q'" in m for m in mensajes)


def test_gaff_identificadores_canonicos_permitidos(tmp_path: Path):
    """Regla 0x0001h (GAFF011): índices de lazo canónicos (i, j, k, n, x, y, z) permitidos."""
    fuente = tmp_path / "canonicos.c"
    fuente.write_text("""
int recorrido(int n)
{
    int total_acumulado = 0;
    for (int i = 0; i < n; i++)
    {
        for (int j = 0; j < n; j++)
        {
            total_acumulado += i + j;
        }
    }
    return total_acumulado;
}
""")
    viols = analizar_archivo(fuente, reglas_habilitadas={"0x0001h"})
    assert len(viols) == 0


def test_gaff_identificadores_cortos_cripticos(tmp_path: Path):
    """Regla 0x0001h (GAFF011): identificadores crípticos (aux, tmp, val, res)."""
    fuente = tmp_path / "cripticos.c"
    fuente.write_text("""
int swap(int primer_valor, int segundo_valor)
{
    int aux = primer_valor;
    int tmp = segundo_valor;
    int res = aux + tmp;
    return res;
}
""")
    viols = analizar_archivo(fuente, reglas_habilitadas={"0x0001h"})
    mensajes = [v.mensaje for v in viols if v.codigo == "0x0001h"]
    assert any("'aux'" in m for m in mensajes)
    assert any("'tmp'" in m for m in mensajes)
    assert any("'res'" in m for m in mensajes)


def test_gaff_identificadores_largos_exceden_limite_iso(tmp_path: Path):
    """Regla 0x0001h (GAFF011): identificadores de variables y funciones que superan 31 caracteres."""
    fuente = tmp_path / "largos.c"
    fuente.write_text("""
void funcion_con_un_nombre_demasiado_largo_que_supera_treinta_y_un_caracteres(void)
{
    int variable_con_un_nombre_extremadamente_largo_que_supera_el_limite_de_longitud = 1;
}
""")
    viols = analizar_archivo(fuente, reglas_habilitadas={"0x0001h"})
    mensajes = [v.mensaje for v in viols if v.codigo == "0x0001h"]
    assert len(mensajes) == 2
    assert any("funcion_con_un_nombre" in m for m in mensajes)
    assert any("variable_con_un_nombre" in m for m in mensajes)


def test_gaff_camel_case_en_variables_y_parametros(tmp_path: Path):
    """Regla 0x0007h (GAFF001): variables locales y parámetros en camelCase."""
    fuente = tmp_path / "camel_vars.c"
    fuente.write_text("""
int calcular(int precioBase, float tasaIva)
{
    int montoTotal = 0;
    for (int indiceIterador = 0; indiceIterador < 10; indiceIterador++)
    {
        montoTotal += indiceIterador;
    }
    return montoTotal;
}
""")
    viols = analizar_archivo(fuente, reglas_habilitadas={"0x0007h"})
    mensajes = [v.mensaje for v in viols if v.codigo == "0x0007h"]
    assert any("'precioBase'" in m for m in mensajes)
    assert any("'tasaIva'" in m for m in mensajes)
    assert any("'montoTotal'" in m for m in mensajes)
    assert any("'indiceIterador'" in m for m in mensajes)


def test_gaff_inicializacion_variables(tmp_path: Path):
    """Regla 0x0003h (GAFF013): variables locales sin inicializar."""
    fuente = tmp_path / "sin_init.c"
    fuente.write_text("""
int calcular(void)
{
    int contador;
    int acumulador = 0;
    return acumulador;
}
""")
    viols = analizar_archivo(fuente, reglas_habilitadas={"0x0003h"})
    assert any(v.codigo == "0x0003h" and "'contador'" in v.mensaje for v in viols)
    assert not any("'acumulador'" in v.mensaje for v in viols)


def test_gaff_numeros_magicos_exhaustivo(tmp_path: Path):
    """Regla 0x300Dh (GAFF006 / GAFF061): números mágicos enteros, flotantes y hex."""
    fuente = tmp_path / "magicos_full.c"
    fuente.write_text("""
#define LIMITE_BUFFER 1024
const int TAM_MAX = 500;
static const double PI = 3.14159;

int evaluar(int valor_entrada)
{
    if (valor_entrada == 42)
    {
        return -1;
    }
    float factor = valor_entrada * 2.5f;
    int mascara = 0xFF;
    return (int)factor + mascara;
}
""")
    viols = analizar_archivo(fuente, reglas_habilitadas={"0x300Dh"})
    mensajes = [v.mensaje for v in viols if v.codigo == "0x300Dh"]
    # 42, 2.5, 0xFF deben ser detectados
    assert any("'42'" in m for m in mensajes)
    assert any("'2.5f'" in m or "'2.5'" in m for m in mensajes)
    assert any("'0xFF'" in m for m in mensajes)
    # -1, LIMITE_BUFFER, TAM_MAX, PI no deben ser detectados
    assert not any("'-1'" in m for m in mensajes)
    assert not any("'1024'" in m for m in mensajes)
    assert not any("'500'" in m for m in mensajes)
    assert not any("'3.14159'" in m for m in mensajes)
