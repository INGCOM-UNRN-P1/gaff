"""GAFF — Linter pedagógico de estilo arquitectónico y convenciones de cátedra."""

from gaff.api import (
    API_VERSION,
    ReporteArchivo,
    ReporteLinting,
    RuleCode,
    ViolacionRegla,
    analizar_archivo,
    analizar_codigo,
    ejecutar_linter,
    normalizar_codigo,
    obtener_regla,
    obtener_severidad,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "API_VERSION",
    "analizar_archivo",
    "analizar_codigo",
    "ejecutar_linter",
    "normalizar_codigo",
    "obtener_regla",
    "obtener_severidad",
    "ReporteLinting",
    "ReporteArchivo",
    "ViolacionRegla",
    "RuleCode",
]

