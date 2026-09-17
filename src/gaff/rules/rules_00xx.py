"""Reglas de estilo de cátedra — Comentarios y estructura documental (rules_00xx)."""

from __future__ import annotations

from typing import List

from gaff.core.contexto import ContextoAnalisis
from gaff.core.models import ViolacionRegla
from gaff.rules import _rules_00xx_espaciado, _rules_00xx_formato


def verificar(ctx: ContextoAnalisis) -> List[ViolacionRegla]:
    """Evalúa las reglas de Comentarios y estructura documental sobre el contexto del archivo."""
    violaciones: List[ViolacionRegla] = []
    violaciones.extend(_rules_00xx_formato.verificar(ctx))
    violaciones.extend(_rules_00xx_espaciado.verificar(ctx))
    return violaciones
