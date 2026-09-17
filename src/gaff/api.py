"""API pública, versionada y documentada de GAFF.

Este módulo define el contrato formal de integración para consumidores externos,
satélites y orquestadores (p. ej., Ripley, Dredd).

Contrato de versión de API: SemVer (API_VERSION = "1.0.0").
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from gaff.core.linter import (
    analizar_archivo as _analizar_archivo,
    analizar_codigo as _analizar_codigo,
    ejecutar_linter as _ejecutar_linter,
)
from gaff.core.models import (
    ReporteArchivo,
    ReporteLinting,
    RuleCode,
    ViolacionRegla,
)
from gaff.core.rules import (
    CATALOGO_REGLAS,
    normalizar_codigo,
    obtener_regla,
    obtener_severidad,
)

API_VERSION: str = "1.0.0"


def analizar_archivo(
    ruta: Union[Path, str],
    reglas_excluidas: Optional[Set[str]] = None,
    reglas_habilitadas: Optional[Set[str]] = None,
) -> List[ViolacionRegla]:
    """Analiza un archivo fuente C y retorna la lista de violaciones de estilo encontradas.

    Parámetros:
        ruta: Ruta al archivo fuente (.c o .h).
        reglas_excluidas: Conjunto de códigos de regla a omitir (ej: {"0x0001h", "0x3001h"}).
        reglas_habilitadas: Conjunto restrictivo de reglas a ejecutar (si es None, ejecuta todas salvo excluidas).

    Retorna:
        Lista de instancias de `ViolacionRegla` con severidad canónica ("ERROR", "ADVERTENCIA", "ESTILO").
    """
    return _analizar_archivo(
        ruta=Path(ruta),
        reglas_excluidas=reglas_excluidas,
        reglas_habilitadas=reglas_habilitadas,
    )


def analizar_codigo(
    codigo: str,
    nombre_archivo: str = "codigo.c",
    reglas_excluidas: Optional[Set[str]] = None,
    reglas_habilitadas: Optional[Set[str]] = None,
) -> List[ViolacionRegla]:
    """Analiza una cadena de código fuente C en memoria."""
    return _analizar_codigo(
        codigo=codigo,
        nombre_archivo=nombre_archivo,
        reglas_excluidas=reglas_excluidas,
        reglas_habilitadas=reglas_habilitadas,
    )


def ejecutar_linter(
    rutas: List[Union[Path, str]],
    recursive: bool = False,
    reglas_excluidas: Optional[Set[str]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> ReporteLinting:
    """Ejecuta el linter sobre múltiples archivos o directorios y consolida el reporte."""
    paths = [Path(p) for p in rutas]
    return _ejecutar_linter(
        rutas=paths,
        recursive=recursive,
        reglas_excluidas=reglas_excluidas,
        config=config,
    )


__all__ = [
    "API_VERSION",
    "analizar_archivo",
    "analizar_codigo",
    "ejecutar_linter",
    "normalizar_codigo",
    "obtener_regla",
    "obtener_severidad",
    "CATALOGO_REGLAS",
    "ReporteLinting",
    "ReporteArchivo",
    "ViolacionRegla",
    "RuleCode",
]
