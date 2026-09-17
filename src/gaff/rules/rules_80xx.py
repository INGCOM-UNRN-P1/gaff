"""Reglas de estilo de cátedra — Compilación y buenas prácticas de ingeniería (rules_80xx)."""

from __future__ import annotations

from typing import List

from gaff.core.contexto import ContextoAnalisis
from gaff.core.models import ViolacionRegla
from gaff.rules import _rules_80xx_compilacion, _rules_80xx_seguridad


def verificar(ctx: ContextoAnalisis) -> List[ViolacionRegla]:
    """Evalúa las reglas de Compilación y buenas prácticas sobre el contexto del archivo."""
    violaciones: List[ViolacionRegla] = []
    violaciones.extend(_rules_80xx_compilacion.verificar(ctx))
    violaciones.extend(_rules_80xx_seguridad.verificar(ctx))
    return violaciones
