"""Cada violación en la taxonomía común del ecosistema (yutani.hallazgos): el código de la regla,
la categoría según su familia y el enlace a la página de la regla en el apunte."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

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


def ruta_relativa(ruta: Any) -> Optional[str]:
    """El archivo como lo esperan jonesy y los demás clientes (yutani.hallazgos.ruta_archivo):
    relativo al directorio de trabajo, con / y sin ./; afuera de él, absoluto."""
    if ruta is None or str(ruta) == "":
        return None
    p = Path(str(ruta).replace("\\", "/")) if not str(ruta).startswith("/") else Path(ruta)
    if p.is_absolute():
        try:
            relativa = os.path.relpath(p, Path.cwd())
        except ValueError:  # otra unidad en Windows
            return p.as_posix()
        if relativa == os.pardir or relativa.startswith(os.pardir + os.sep):
            return p.as_posix()
        p = Path(relativa)
    return Path(os.path.normpath(p)).as_posix()


def a_hallazgo(v: ViolacionRegla) -> Dict[str, Any]:
    codigo = str(v.codigo)
    datos: Dict[str, Any] = hallazgo("gaff", codigo, categoria(codigo), v.severidad or "estilo", v.mensaje,
                                     archivo=ruta_relativa(v.archivo), linea=v.linea or None,
                                     columna=v.columna or None, sugerencia=v.sugerencia or None)
    # El porqué de la regla (lo que jonesy muestra con F1), clave opcional de la forma común.
    descripcion = CATALOGO_REGLAS.get(codigo, {}).get("descripcion", "")
    if descripcion:
        datos["explicacion"] = descripcion
    return datos
