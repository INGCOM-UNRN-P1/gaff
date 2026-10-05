"""Caracterización de aplicar_autofix_archivo sobre los ejemplos (revisión 07: partir la función).

golden_autofix.json se generó antes de partirla (tests/caracterizacion/generar_golden_autofix.py).
"""

import importlib.util
import json
from pathlib import Path

DIRECTORIO = Path(__file__).parent / "caracterizacion"
_spec = importlib.util.spec_from_file_location("generar_golden_autofix", DIRECTORIO / "generar_golden_autofix.py")
_generador = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_generador)


def test_mismas_correcciones_que_antes_del_refactor():
    esperado = json.loads((DIRECTORIO / "golden_autofix.json").read_text(encoding="utf-8"))
    assert _generador.golden() == esperado
