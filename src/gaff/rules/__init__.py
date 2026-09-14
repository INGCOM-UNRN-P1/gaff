"""Paquetes modulares de reglas de estilo de cátedra de GAFF."""

from __future__ import annotations

from typing import List

from gaff.core.contexto import ContextoAnalisis
from gaff.core.models import ViolacionRegla
from gaff.rules import (
    rules_00xx,
    rules_10xx,
    rules_20xx,
    rules_30xx,
    rules_40xx,
    rules_50xx,
    rules_60xx,
    rules_70xx,
    rules_80xx,
)

MODULOS_REGLAS = [
    rules_00xx,
    rules_10xx,
    rules_20xx,
    rules_30xx,
    rules_40xx,
    rules_50xx,
    rules_60xx,
    rules_70xx,
    rules_80xx,
]


def ejecutar_todas_las_familias(ctx: ContextoAnalisis) -> List[ViolacionRegla]:
    """Ejecuta todos los módulos de reglas sobre el contexto de análisis dado."""
    violaciones: List[ViolacionRegla] = []
    for mod in MODULOS_REGLAS:
        violaciones.extend(mod.verificar(ctx))
    return violaciones
