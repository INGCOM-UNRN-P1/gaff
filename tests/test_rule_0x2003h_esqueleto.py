"""`gaff fix` no debe dar por documentada una función con un esqueleto vacío (N-GAFF-02).

Antes, el autofix de 0x2003h insertaba «@brief Descripción de la función f.»
y la regla dejaba de avisar: un estudiante cumplía la regla sin escribir
una sola palabra de documentación.
"""

from __future__ import annotations

from pathlib import Path

from gaff.core.linter import analizar_archivo, aplicar_autofix_archivo

CODIGO = """int sumar(int a, int b)
{
    return a + b;
}
"""


def _avisos_0x2003h(fuente: Path):
    return [v for v in analizar_archivo(fuente, reglas_habilitadas={"0x2003h"}) if v.codigo == "0x2003h"]


def test_fix_inserta_esqueleto_marcado_y_la_regla_sigue_avisando(tmp_path: Path):
    fuente = tmp_path / "suma.c"
    fuente.write_text(CODIGO, encoding="utf-8")
    assert len(_avisos_0x2003h(fuente)) == 1

    aplicar_autofix_archivo(fuente, reglas_habilitadas={"0x2003h"})
    texto = fuente.read_text(encoding="utf-8")
    assert "@brief [completar: qué hace sumar]" in texto
    assert "@param a [completar:" in texto
    assert "@return [completar:" in texto

    avisos = _avisos_0x2003h(fuente)
    assert len(avisos) == 1
    assert "esqueleto sin completar" in avisos[0].mensaje
    assert avisos[0].es_autofixable is False


def test_esqueleto_de_versiones_anteriores_tampoco_cuenta(tmp_path: Path):
    fuente = tmp_path / "suma.c"
    fuente.write_text(
        "/**\n * @brief Descripción de la función sumar.\n *\n"
        " * @param a Descripción del parámetro a.\n * @param b Descripción del parámetro b.\n"
        " * @return Descripción del valor de retorno.\n */\n" + CODIGO,
        encoding="utf-8",
    )
    avisos = _avisos_0x2003h(fuente)
    assert len(avisos) == 1
    assert "esqueleto sin completar" in avisos[0].mensaje


def test_documentacion_real_no_genera_aviso(tmp_path: Path):
    fuente = tmp_path / "suma.c"
    fuente.write_text(
        "/**\n * @brief Suma dos enteros.\n *\n * @param a primer sumando.\n"
        " * @param b segundo sumando.\n * @return la suma de a y b.\n */\n" + CODIGO,
        encoding="utf-8",
    )
    assert _avisos_0x2003h(fuente) == []


def test_esqueleto_a_medio_completar_sigue_avisando(tmp_path: Path):
    fuente = tmp_path / "suma.c"
    fuente.write_text(
        "/**\n * @brief Suma dos enteros.\n *\n * @param a primer sumando.\n"
        " * @param b [completar: qué representa b]\n * @return la suma de a y b.\n */\n" + CODIGO,
        encoding="utf-8",
    )
    assert len(_avisos_0x2003h(fuente)) == 1
