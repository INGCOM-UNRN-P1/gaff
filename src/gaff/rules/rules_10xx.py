"""Reglas de estilo de cátedra — Nomenclatura e identificadores (rules_10xx)."""

from __future__ import annotations

from typing import List

from gaff.core.contexto import ContextoAnalisis
from gaff.core.models import ViolacionRegla
from gaff.rules import _rules_10xx_identificadores, _rules_10xx_variables


def verificar(ctx: ContextoAnalisis) -> List[ViolacionRegla]:
    """Evalúa las reglas de Nomenclatura e identificadores sobre el contexto del archivo."""
    violaciones: List[ViolacionRegla] = []
    violaciones.extend(_rules_10xx_variables.verificar(ctx))
    violaciones.extend(_rules_10xx_identificadores.verificar(ctx))
    return violaciones
