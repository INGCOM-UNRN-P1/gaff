"""Severidad por actividad y reglas de P1 (QoL #388, #390, #391)."""

from pathlib import Path

import pytest

from gaff.core.config import aplicar_severidades_por_actividad
from gaff.core.linter import ejecutar_linter

FUENTE = """#include <stdio.h>
#define N 10

int main(void)
{
    int matriz[3][4];
    char palabra[4] = "Hola";
    char corta[N] = "Hola";
    char escape[2] = "a\\n";
    for (int i = 0; i < N; i++)
    {
        if (i == 2)
        {
            i++;
        }
    }
    printf("%s %s %s %d\\n", palabra, corta, escape, matriz[0][0]);
    return 0;
}
"""


def _violaciones(tmp_path: Path, config_yaml: str = "") -> list:
    (tmp_path / "p.c").write_text(FUENTE, encoding="utf-8")
    if config_yaml:
        (tmp_path / ".gaffrc.yaml").write_text(config_yaml, encoding="utf-8")
    return [v for a in ejecutar_linter([tmp_path / "p.c"]).archivos for v in a.violaciones]


def test_reglas_de_p1(tmp_path):
    por_linea = {(str(v.codigo), v.linea) for v in _violaciones(tmp_path)}
    assert ("0x5001h", 6) in por_linea                      # matriz con números mágicos (#388)
    assert ("0x0014h", 7) in por_linea                      # sin lugar para '\0' (#390)
    assert ("0x0014h", 8) not in por_linea                  # N es una constante: no se evalúa
    assert ("0x0014h", 9) in por_linea                      # "a\n" son 2 caracteres: falta el lugar del '\0'
    assert any(c == "0x301Bh" for c, _ in por_linea)        # contador del for modificado (#391)


def test_solo_las_familias_de_la_actividad(tmp_path):
    todas = _violaciones(tmp_path)
    solo_formato = _violaciones(tmp_path, "familias: [formato]\n")
    assert solo_formato and len(solo_formato) < len(todas)
    from gaff.core.rules import CATALOGO_REGLAS
    assert {CATALOGO_REGLAS[str(v.codigo)]["directorio"] for v in solo_formato} == {"00_formato"}


def test_severidad_por_codigo_familia_y_off(tmp_path):
    vs = _violaciones(tmp_path, 'severidades:\n  formato: error\n  "0x5001h": "off"\n  control: advertencia\n')
    assert not any(str(v.codigo) == "0x5001h" for v in vs)
    assert all(v.severidad == "ERROR" for v in vs if str(v.codigo) == "0x0014h")


def test_severidad_invalida():
    with pytest.raises(ValueError, match="inválida"):
        aplicar_severidades_por_actividad([], {"severidades": {"formato": "grave"}})
