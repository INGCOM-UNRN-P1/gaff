"""Reglas de estilo de cátedra — Funciones y diseño modular (rules_40xx)."""

from __future__ import annotations

from typing import List

from gaff.core.contexto import ContextoAnalisis
from gaff.core.models import ViolacionRegla
from gaff.rules import _rules_40xx_complejidad, _rules_40xx_modularidad


def verificar(ctx: ContextoAnalisis) -> List[ViolacionRegla]:
    """Evalúa las reglas de Funciones y diseño modular sobre el contexto del archivo."""
    violaciones: List[ViolacionRegla] = []
    violaciones.extend(_rules_40xx_complejidad.verificar(ctx))
    violaciones.extend(_rules_40xx_modularidad.verificar(ctx))
    return violaciones
