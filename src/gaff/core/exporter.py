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
        "| Código Hex | Alias | Severidad | Nombre / Título | Descripción y Sugerencia | Autofix |",
        "| :---: | :---: | :---: | :--- | :--- | :---: |",
    ]
    
    for cod, regla in sorted(CATALOGO_REGLAS.items()):
        if not cod.startswith("0x"):
            continue
        alias = regla.get("alias", "-")
        sev = regla.get("severidad", "ADVERTENCIA")
        titulo = regla.get("titulo", "Regla")
        desc = regla.get("descripcion", "").replace("\n", " ")
        fix = "✓ Sí" if regla.get("autofixable", False) or regla.get("autofix") == "Sí" else "No"
        lineas.append(f"| `{cod}` | `{alias}` | **{sev}** | **{titulo}** | {desc} | {fix} |")
        
    lineas.append("")
    lineas.append("---")
    lineas.append("Generado automáticamente por `gaff export-rules`.")
    return "\n".join(lineas)
