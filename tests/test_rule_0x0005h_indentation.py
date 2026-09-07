"""Tests unitarios para la verificación de indentación en múltiplos de 4 espacios (0x0005h)."""

from pathlib import Path
from gaff.core.linter import analizar_archivo, aplicar_autofix_archivo, ejecutar_linter
from gaff.core.rules import CATALOGO_REGLAS


def test_catalogo_regla_0x0005h():
    assert "0x0005h" in CATALOGO_REGLAS
    regla = CATALOGO_REGLAS["0x0005h"]
    assert "cuatro espacios" in regla["titulo"]
    assert regla["autofix"] == "Sí"


def test_indentacion_valida_multiplos_de_cuatro(tmp_path: Path):
    src = tmp_path / "valido.c"
    src.write_text("""#include <stdio.h>

void funcion(void)
{
    int x = 10;
    if (x > 5)
    {
        for (int i = 0; i < x; i++)
        {
            printf("%d\\n", i);
        }
    }
}
""")
    viols = analizar_archivo(src, reglas_habilitadas={"0x0005h"})
    assert len(viols) == 0


def test_detectar_indentacion_dos_espacios(tmp_path: Path):
    src = tmp_path / "dos_espacios.c"
    src.write_text("""void test(void)
{
  int x = 10;
}
""")
    viols = analizar_archivo(src, reglas_habilitadas={"0x0005h"})
    indent_viols = [v for v in viols if "no es múltiplo de 4" in v.mensaje]
    assert len(indent_viols) == 1
    assert indent_viols[0].linea == 3
    assert indent_viols[0].codigo == "0x0005h"
    assert "2 espacios" in indent_viols[0].mensaje


def test_detectar_indentacion_seis_espacios(tmp_path: Path):
    src = tmp_path / "seis_espacios.c"
    src.write_text("""void test(void)
{
    if (1)
    {
      int y = 20;
    }
}
""")
    # Línea 5 tiene 6 espacios (debería tener 8)
    viols = analizar_archivo(src, reglas_habilitadas={"0x0005h"})
    indent_viols = [v for v in viols if "no es múltiplo de 4" in v.mensaje]
    assert len(indent_viols) == 1
    assert indent_viols[0].linea == 5
    assert "6 espacios" in indent_viols[0].mensaje


def test_comentarios_de_bloque_no_generan_falsos_positivos(tmp_path: Path):
    src = tmp_path / "comentarios.c"
    src.write_text("""/**
 * @brief Función de prueba.
 * @param a Parametro.
 * @return Entero.
 */
int test(int a)
{
    /* Comentario interno
     * con alineación de asterisco
     */
    return a;
}
""")
    viols = analizar_archivo(src, reglas_habilitadas={"0x0005h"})
    assert len(viols) == 0


def test_autofix_indentacion_multiplo_de_cuatro(tmp_path: Path):
    src = tmp_path / "autofix_indent.c"
    src.write_text("""void test(void)
{
  int x = 10;
  if (x > 0)
  {
      int y = 20;
  }
}
""")
    arreglos = aplicar_autofix_archivo(src)
    assert arreglos > 0

    contenido = src.read_text(encoding="utf-8")
    assert "    int x = 10;" in contenido
    assert "        int y = 20;" in contenido

    # Tras autofix no deben quedar violaciones de 0x0005h
    viols = analizar_archivo(src, reglas_habilitadas={"0x0005h"})
    assert len(viols) == 0


def test_exclusion_por_regla(tmp_path: Path):
    src = tmp_path / "excluido.c"
    src.write_text("""void test(void)
{
  int x = 10;
}
""")
    viols = analizar_archivo(src, reglas_excluidas={"0x0005h"})
    assert not any(v.codigo == "0x0005h" for v in viols)
