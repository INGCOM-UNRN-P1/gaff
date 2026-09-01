"""Plugin de GAFF para integración transparente con RIPLEY."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from gaff.core.linter import ejecutar_linter


class GaffPlugin:
    """Plugin linter de estilo y convenciones arquitectónicas para Ripley."""

    name = "style"
    version = "0.1.0"

    def is_available(self) -> bool:
        return True

    def execute(self, workspace: Path, manifest_config: Dict[str, Any]) -> Dict[str, Any]:
        excluidas = set(
            manifest_config.get("excluded_rules", [])
            or manifest_config.get("disabled_rules", [])
            or manifest_config.get("exclude", [])
            or manifest_config.get("ignore", [])
            or manifest_config.get("reglas_excluidas", [])
        )
        reporte = ejecutar_linter(
            [workspace],
            fix=False,
            reglas_excluidas=excluidas if excluidas else None,
            recursive=True,
        )
        observaciones = []

        for f_rep in reporte.archivos:
            for v in f_rep.violaciones:
                observaciones.append({
                    "codigo": str(v.codigo),
                    "rule_code": str(v.codigo),
                    "rule_name": v.titulo,
                    "severidad": "ADVERTENCIA" if v.severidad == "ESTILO" else v.severidad,
                    "archivo": Path(v.archivo).name,
                    "linea": v.linea,
                    "columna": v.columna,
                    "mensaje": v.mensaje,
                    "sugerencia": v.sugerencia,
                    "es_autofixable": v.es_autofixable,
                })

        return {
            "ok": reporte.ok,
            "total_violaciones": reporte.total_violaciones,
            "observaciones": observaciones,
        }
