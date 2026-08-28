"""Modelos de datos para el motor de linting de GAFF."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


class RuleCode(str):
    """Representa un código de regla de cátedra (ej. '0x0007h') con alias retrocompatible ('GAFF001')."""

    def __new__(cls, code: str, alias: Optional[str] = None):
        obj = super().__new__(cls, code)
        obj._alias = alias or ""
        return obj

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return super().__eq__(other) or (bool(getattr(self, "_alias", None)) and self._alias.lower() == other.lower())
        return super().__eq__(other)

    def __hash__(self) -> int:
        return super().__hash__()


@dataclass
class ViolacionRegla:
    """Representa una violación de estilo encontrada en el código."""
    codigo: RuleCode | str        # 0x0007h, 0x3004h, etc.
    titulo: str
    archivo: Path
    linea: int
    columna: int
    mensaje: str
    sugerencia: str
    codigo_linea: str = ""
    es_autofixable: bool = False
    severidad: str = "ESTILO"     # ESTILO, ADVERTENCIA, ERROR

    def to_dict(self) -> Dict[str, Any]:
        return {
            "codigo": str(self.codigo),
            "alias": getattr(self.codigo, "_alias", ""),
            "titulo": self.titulo,
            "archivo": str(self.archivo),
            "linea": self.linea,
            "columna": self.columna,
            "mensaje": self.mensaje,
            "sugerencia": self.sugerencia,
            "codigo_linea": self.codigo_linea,
            "es_autofixable": self.es_autofixable,
            "severidad": self.severidad,
        }


@dataclass
class ReporteArchivo:
    """Resultado del linting sobre un archivo individual."""
    archivo: Path
    violaciones: List[ViolacionRegla] = field(default_factory=list)
    arreglos_aplicados: int = 0

    @property
    def ok(self) -> bool:
        return len(self.violaciones) == 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "archivo": str(self.archivo),
            "ok": self.ok,
            "total_violaciones": len(self.violaciones),
            "arreglos_aplicados": self.arreglos_aplicados,
            "violaciones": [v.to_dict() for v in self.violaciones],
        }


@dataclass
class ReporteLinting:
    """Reporte consolidado de linting sobre un conjunto de archivos."""
    archivos: List[ReporteArchivo] = field(default_factory=list)

    @property
    def total_violaciones(self) -> int:
        return sum(len(a.violaciones) for a in self.archivos)

    @property
    def total_arreglos(self) -> int:
        return sum(a.arreglos_aplicados for a in self.archivos)

    @property
    def ok(self) -> bool:
        return self.total_violaciones == 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "total_archivos": len(self.archivos),
            "total_violaciones": self.total_violaciones,
            "total_arreglos": self.total_arreglos,
            "archivos": [a.to_dict() for a in self.archivos],
        }
