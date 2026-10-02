"""Cada violación en la taxonomía común del ecosistema (yutani.hallazgos): el código de la regla,
la categoría según su familia y el enlace a la página de la regla en el apunte."""

from __future__ import annotations

from typing import Any, Dict

from yutani.hallazgos import hallazgo

from gaff.core.models import ViolacionRegla
from gaff.core.rules import CATALOGO_REGLAS

# Familia de reglas (directorio del apunte) → categoría común.
CATEGORIA_POR_FAMILIA = {
    "00_formato": "estilo",
    "01_nomenclatura": "estilo",
    "02_documentacion": "documentacion",
    "10_control": "control",
    "20_funciones": "funciones",
    "30_memoria": "memoria",
    "40_archivos": "archivos",
    "50_seguridad": "seguridad",
    "60_proceso": "compilacion",
    "70_robustez": "funciones",
    "80_verificacion": "pruebas",
}


def categoria(codigo: str) -> str:
    familia = CATALOGO_REGLAS.get(codigo, {}).get("directorio", "")
    return CATEGORIA_POR_FAMILIA.get(familia, "estilo")


def a_hallazgo(v: ViolacionRegla) -> Dict[str, Any]:
    codigo = str(v.codigo)
    datos: Dict[str, Any] = hallazgo("gaff", codigo, categoria(codigo), v.severidad or "estilo", v.mensaje,
                                     archivo=str(v.archivo), linea=v.linea, columna=v.columna,
                                     sugerencia=v.sugerencia or None)
    return datos
