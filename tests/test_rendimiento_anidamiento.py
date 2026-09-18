"""Regresión de GAFF-D0303: `gaff check` tardaba ~9 s con 300 `if` anidados.

Dos causas separadas:
- la regla de espacios antes de `;`/`,` usaba `[ \\t]+([;,])`: en una racha de k espacios el
  motor reintentaba desde cada posición interior, O(k^2) por línea (arreglado);
- el resto es proporcional al tamaño del archivo, no a la profundidad: con 300 niveles la
  sangría suma más de 350 KB. Un archivo plano del mismo tamaño tarda lo mismo.
"""

import time
from pathlib import Path

import pytest

from gaff.core.linter import analizar_archivo
from gaff.rules._rules_00xx_espaciado import RE_ESPACIO_ANTES_DE_SEPARADOR

MENSAJE = "Espacio en blanco innecesario antes del separador"


def _analizar(tmp_path: Path, fuente: str):
    ruta = tmp_path / "caso.c"
    ruta.write_text(fuente, encoding="utf-8")
    return analizar_archivo(ruta)


def _mensajes(violaciones):
    return [v.mensaje for v in violaciones if MENSAJE in v.mensaje]


def _anidado(n: int) -> str:
    return (
        "int main(void) {\n"
        + "".join("    " * (i + 1) + "if (1) {\n" for i in range(n))
        + "    " * (n + 1) + "return 0;\n"
        + "".join("    " * (n - i) + "}\n" for i in range(n))
        + "}\n"
    )


def test_la_regex_no_tiene_backtracking_cuadratico():
    # Con el patrón anterior, una racha de 200 000 espacios sin `;` detrás tardaba horas.
    linea = "int x = 1" + " " * 200_000 + "+ 2"
    t0 = time.perf_counter()
    assert RE_ESPACIO_ANTES_DE_SEPARADOR.search(linea) is None
    assert time.perf_counter() - t0 < 0.5


@pytest.mark.parametrize(
    "linea, esperados",
    [
        ("int a = 1 ;", [";"]),
        ("int b = 2 , c = 3;", [","]),
        ("    ;", [";"]),
        ("a   ,   b  ;", [",", ";"]),
        ("int a = 1;", []),
        ("f(a, b);", []),
    ],
)
def test_la_regex_sigue_detectando_los_mismos_casos(linea, esperados):
    assert [m.group(1) for m in RE_ESPACIO_ANTES_DE_SEPARADOR.finditer(linea)] == esperados


def test_los_espacios_antes_de_separadores_se_siguen_detectando_en_el_linter(tmp_path):
    fuente = "int main(void) {\n    int a = 1 ;\n    int b = 2 , c = 3;\n    return a;\n}\n"
    mensajes = _mensajes(_analizar(tmp_path, fuente))
    assert len(mensajes) == 2
    assert any("';'" in m for m in mensajes) and any("','" in m for m in mensajes)


def test_un_separador_pegado_no_se_marca(tmp_path):
    fuente = "int main(void) {\n    int a = 1;\n    int b = 2, c = 3;\n    return a;\n}\n"
    assert _mensajes(_analizar(tmp_path, fuente)) == []


def test_la_profundidad_de_anidamiento_no_agrega_costo_por_si_sola(tmp_path):
    """Un archivo anidado y uno plano de igual tamaño y sangría tardan lo mismo."""
    n = 120
    anidado = _anidado(n)
    plano = "int main(void) {\n" + "".join(
        l.replace("if (1) {", "x = 1;").replace("}", "y = 2;") + "\n" for l in anidado.split("\n")[1:-2]
    ) + "}\n"

    def medir(fuente: str) -> float:
        t0 = time.perf_counter()
        _analizar(tmp_path, fuente)
        return time.perf_counter() - t0

    medir(anidado)  # calienta
    t_anidado, t_plano = medir(anidado), medir(plano)
    assert t_anidado < max(t_plano * 2.0, 0.3)
