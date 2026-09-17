"""Modelos de datos para el motor de linting de GAFF."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional


class RuleCode(str):
    """Representa un código de regla de cátedra (ej. '0x0102h') con soporte de retrocompatibilidad y severidad."""

    def __new__(
        cls,
        code: str,
        alias: Optional[str] = None,
        codigo_anterior: Optional[str] = None,
        severidad: Optional[str] = None,
        *args,
        **kwargs,
    ):
        obj = super().__new__(cls, code)
        obj._alias = alias or ""
        obj._codigo_anterior = codigo_anterior or ""
        obj._severidad = severidad or "ESTILO"
        return obj

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            other_low = other.lower()
            return (
                super().__eq__(other)
                or self.lower() == other_low
                or (bool(getattr(self, "_alias", None)) and self._alias.lower() == other_low)
                or (bool(getattr(self, "_codigo_anterior", None)) and self._codigo_anterior.lower() == other_low)
            )
        return super().__eq__(other)

    @property
    def alias(self) -> str:
        return getattr(self, "_alias", "")

    @property
    def codigo_anterior(self) -> str:
        return getattr(self, "_codigo_anterior", "")

    @property
    def severidad(self) -> str:
        return getattr(self, "_severidad", "ESTILO")

    @property
    def es_error(self) -> bool:
        """Indica si la regla constituye un error crítico (memoria, UB, seguridad)."""
        return self.severidad.upper() == "ERROR"

    @property
    def es_advertencia(self) -> bool:
        """Indica si la regla constituye una advertencia de diseño o flujo."""
        return self.severidad.upper() == "ADVERTENCIA"

    @property
    def es_estilo(self) -> bool:
        """Indica si la regla es puramente de formato, espaciado o nomenclatura."""
        return self.severidad.upper() == "ESTILO"

    @property
    def familia(self) -> str:
        """Retorna el prefijo de familia canónica (ej: '0x00XX', '0x30XX')."""
        if len(self) >= 4 and self.lower().startswith("0x"):
            return f"0x{self[2:4].upper()}XX"
        return "GENERAL"

    def __hash__(self) -> int:
        return super().__hash__()


class ReglaInfo(NamedTuple):
    """Información canónica de una regla de estilo con tipado enriquecido."""
    codigo: RuleCode
    titulo: str

    @property
    def severidad(self) -> str:
        return self.codigo.severidad

    @property
    def alias(self) -> str:
        return self.codigo.alias

    @property
    def codigo_anterior(self) -> str:
        return self.codigo.codigo_anterior

    @property
    def familia(self) -> str:
        return self.codigo.familia


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

    def __post_init__(self) -> None:
        # Si la severidad no fue explicitada como ADVERTENCIA/ERROR, consultar severidad canónica
        if self.severidad == "ESTILO":
            if isinstance(self.codigo, RuleCode) and self.codigo.severidad != "ESTILO":
                self.severidad = self.codigo.severidad
            else:
                try:
                    from gaff.core.rules import obtener_severidad
                    sev = obtener_severidad(str(self.codigo))
                    if sev != "ESTILO":
                        self.severidad = sev
                except (ImportError, Exception):
                    pass

    def to_dict(self) -> Dict[str, Any]:
        return {
            "codigo": str(self.codigo),
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
            "schema_version": "1.0.0",
            "ok": self.ok,
            "total_archivos": len(self.archivos),
            "total_violaciones": self.total_violaciones,
            "total_arreglos": self.total_arreglos,
            "archivos": [a.to_dict() for a in self.archivos],
        }
