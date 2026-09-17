"""Reglas de estilo de cátedra — Punteros y gestión de memoria (rules_60xx)."""

from __future__ import annotations

from typing import List

from gaff.core.contexto import ContextoAnalisis
from gaff.core.models import ViolacionRegla
from gaff.rules import _rules_60xx_memoria, _rules_60xx_punteros


def verificar(ctx: ContextoAnalisis) -> List[ViolacionRegla]:
    """Evalúa las reglas de Punteros y gestión de memoria sobre el contexto del archivo."""
    violaciones: List[ViolacionRegla] = []
    violaciones.extend(_rules_60xx_punteros.verificar(ctx))
    violaciones.extend(_rules_60xx_memoria.verificar(ctx))
    return violaciones
