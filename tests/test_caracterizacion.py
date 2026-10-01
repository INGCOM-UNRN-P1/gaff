"""Caracterización de las reglas de gaff sobre sus ejemplos (N-GAFF-04).

golden.json se generó antes de partir cada `verificar` en una función por regla: si este test falla,
el refactor cambió alguna violación o su orden. Ver tests/caracterizacion/generar_golden.py.
"""

import importlib.util
import json
from pathlib import Path

import pytest

DIRECTORIO = Path(__file__).parent / "caracterizacion"
_spec = importlib.util.spec_from_file_location("generar_golden_gaff", DIRECTORIO / "generar_golden.py")
_generador = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_generador)

GOLDEN = json.loads((DIRECTORIO / "golden.json").read_text(encoding="utf-8"))


def test_el_golden_cubre_todos_los_ejemplos():
    assert set(GOLDEN) == {str(r.relative_to(_generador.RAIZ)) for r in _generador.ejemplos()}


@pytest.mark.parametrize("ejemplo", sorted(GOLDEN))
def test_mismas_violaciones_que_antes_del_refactor(ejemplo):
    assert _generador.violaciones(_generador.RAIZ / ejemplo) == GOLDEN[ejemplo]
