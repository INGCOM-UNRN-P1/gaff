"""Exportador de guía de estilo y catálogo de reglas a Markdown institucional en GAFF."""

from __future__ import annotations

from typing import Dict, Any
from gaff.core.rules import CATALOGO_REGLAS


def generar_guia_estilo_markdown() -> str:
    """Genera un documento Markdown completo con el catálogo de reglas de estilo de la cátedra."""
    lineas = [
        "# Manual de Convenciones y Estilo Arquitectónico en C",
        "",
        "**Cátedra de Programación en C / Arquitectura de Computadores**  ",
        "Este documento recopila las reglas formales de estilo y sintaxis verificadas automáticamente por `gaff`.",
        "",
        "---",
        "",
        "## Catálogo Oficial de Reglas",
        "",
        "| Código Hex | Severidad | Nombre / Título | Descripción y Sugerencia | Autofix |",
        "| :---: | :---: | :--- | :--- | :---: |",
    ]
    
    for cod, regla in sorted(CATALOGO_REGLAS.items()):
        if not cod.startswith("0x"):
            continue
        sev = regla.get("severidad", "ADVERTENCIA")
        titulo = regla.get("titulo", "Regla")
        desc = regla.get("descripcion", "").replace("\n", " ")
        fix = "✓ Sí" if regla.get("autofixable", False) or regla.get("autofix") == "Sí" else "No"
        lineas.append(f"| `{cod}` | **{sev}** | **{titulo}** | {desc} | {fix} |")
    lineas.append("---")
    lineas.append("Generado automáticamente por `gaff export-rules`.")
    return "\n".join(lineas)


def generar_sarif_210(reporte) -> Dict[str, Any]:
    """Genera un payload JSON conforme a la especificación estándar OASIS SARIF 2.1.0."""
    from gaff import __version__

    sarif_rules = []
    reglas_vistas = set()

    results = []
    for rep_arch in reporte.archivos:
        for v in rep_arch.violaciones:
            c_str = str(v.codigo)
            if c_str not in reglas_vistas:
                reglas_vistas.add(c_str)
                sarif_rules.append({
                    "id": c_str,
                    "name": v.titulo,
                    "shortDescription": {"text": v.titulo},
                    "fullDescription": {"text": v.mensaje},
                    "defaultConfiguration": {
                        "level": "error" if v.severidad == "ERROR" else "warning"
                    },
                })

            results.append({
                "ruleId": c_str,
                "level": "error" if v.severidad == "ERROR" else "warning",
                "message": {"text": f"{v.mensaje} Sugerencia: {v.sugerencia}"},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": str(v.archivo),
                            },
                            "region": {
                                "startLine": max(1, v.linea),
                                "startColumn": max(1, v.columna),
                            },
                        }
                    }
                ],
            })

    return {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "gaff",
                        "version": __version__,
                        "informationUri": "https://github.com/unsam/gaff",
                        "rules": sarif_rules,
                    }
                },
                "results": results,
            }
        ],
    }


def generar_github_summary(reporte) -> str:
    """Genera un resumen en formato GitHub Flavored Markdown adecuado para $GITHUB_STEP_SUMMARY."""
    estado_badge = "✅ Aprobado (Sin Violaciones)" if reporte.ok else f"❌ Requiere Revisión ({reporte.total_violaciones} violaciones)"

    total_errores = sum(1 for a in reporte.archivos for v in a.violaciones if getattr(v, "severidad", "ADVERTENCIA") == "ERROR")
    total_advertencias = sum(1 for a in reporte.archivos for v in a.violaciones if getattr(v, "severidad", "ADVERTENCIA") != "ERROR")

    lines = [
        "## 🛡️ Gaff Linter — Resumen de Cumplimiento de Estilo",
        "",
        "| Métrica | Valor |",
        "| :--- | :--- |",
        f"| **Estado General** | {estado_badge} |",
        f"| **Archivos Auditados** | `{len(reporte.archivos)}` |",
        f"| **Total Violaciones** | `{reporte.total_violaciones}` |",
        f"| **Errores Críticos** | `{total_errores}` |",
        f"| **Advertencias de Estilo** | `{total_advertencias}` |",
    ]
    if reporte.total_arreglos > 0:
        lines.append(f"| **Autofixes Aplicados** | `{reporte.total_arreglos}` |")

    lines.append("")

    if reporte.ok:
        lines.append("> [!NOTE]")
        lines.append("> **100% Conforme:** Todo el código evaluado cumple estrictamente con las convenciones arquitectónicas y normas de estilo institucional.")
        lines.append("")
    else:
        lines.append("### 📋 Detalle de Observaciones por Archivo")
        lines.append("")
        lines.append("| Archivo | Ubicación | Regla | Severidad | Descripción | Autofix |")
        lines.append("| :--- | :---: | :---: | :---: | :--- | :---: |")
        for rep_arch in reporte.archivos:
            fname = rep_arch.archivo.name
            for v in rep_arch.violaciones:
                fix_str = "✓ Sí" if v.es_autofixable else "No"
                sev_icon = "🔴 ERROR" if getattr(v, "severidad", "ADVERTENCIA") == "ERROR" else "🟡 WARN"
                lines.append(f"| `{fname}` | L{v.linea}:{v.columna} | `{v.codigo}` | {sev_icon} | {v.mensaje} | {fix_str} |")
        lines.append("")

    return "\n".join(lines)

