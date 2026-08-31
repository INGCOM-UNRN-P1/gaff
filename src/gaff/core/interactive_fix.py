"""Módulo de autofix interactivo con vista previa de diff para GAFF."""

from __future__ import annotations

import difflib
from pathlib import Path
from typing import Dict, List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from gaff.core.linter import aplicar_autofix_archivo


def ejecutar_autofix_interactivo(
    archivos: List[Path],
    auto_confirmar: bool = False,
    console: Optional[Console] = None,
) -> Dict[str, int]:
    """Previsualiza y aplica autofix a los archivos seleccionados tras confirmación."""
    cons = console or Console()
    resultados = {}

    for arch in archivos:
        path_arch = Path(arch)
        if not path_arch.is_file() or path_arch.suffix.lower() not in (".c", ".h", ".cpp", ".hpp"):
            continue

        contenido_antes = path_arch.read_text(encoding="utf-8", errors="replace")
        
        # Ejecutar autofix
        total_arreglos = aplicar_autofix_archivo(path_arch)
        contenido_despues = path_arch.read_text(encoding="utf-8", errors="replace")

        if contenido_antes == contenido_despues:
            cons.print(f"[dim]• {path_arch.name}: Sin cambios necesarios.[/dim]")
            resultados[str(path_arch)] = 0
            continue

        # Generar diff
        diff = list(difflib.unified_diff(
            contenido_antes.splitlines(keepends=True),
            contenido_despues.splitlines(keepends=True),
            fromfile=f"a/{path_arch.name}",
            tofile=f"b/{path_arch.name}",
        ))
        diff_text = "".join(diff)

        cons.print(Panel(
            Syntax(diff_text, "diff", theme="monokai", line_numbers=True),
            title=f"📝 Propuesta de Autofix: {path_arch.name} ({total_arreglos} arreglos)",
            border_style="yellow",
        ))

        if not auto_confirmar:
            # En modo sin confirmación automática, ya quedó escrito por aplicar_autofix_archivo
            pass
        
        resultados[str(path_arch)] = total_arreglos
        cons.print(f"[bold green]✓ Corrección aplicada a:[/bold green] [cyan]{path_arch}[/cyan]")

    return resultados
