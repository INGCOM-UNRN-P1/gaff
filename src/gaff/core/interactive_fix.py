"""Módulo de autofix interactivo con vista previa de diff para GAFF."""

from __future__ import annotations

import difflib
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.syntax import Syntax

from gaff.core.linter import aplicar_autofix_archivo


def ejecutar_autofix_interactivo(
    archivos: List[Path],
    auto_confirmar: bool = False,
    console: Optional[Console] = None,
    reglas_excluidas: Optional[Set[str]] = None,
    reglas_habilitadas: Optional[Set[str]] = None,
    idkfa: bool = False,
) -> Dict[str, int]:
    """Previsualiza y aplica autofix a los archivos seleccionados tras confirmación interactiva [y/n/q]."""
    cons = console or Console()
    resultados: Dict[str, int] = {}

    for arch in archivos:
        path_arch = Path(arch)
        if not path_arch.is_file() or path_arch.suffix.lower() not in (".c", ".h", ".cpp", ".hpp"):
            continue

        contenido_antes = path_arch.read_text(encoding="utf-8", errors="replace")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir) / path_arch.name
            shutil.copy2(path_arch, tmp_path)
            total_arreglos = aplicar_autofix_archivo(
                tmp_path,
                reglas_excluidas=reglas_excluidas,
                reglas_habilitadas=reglas_habilitadas,
                idkfa=idkfa,
            )
            contenido_despues = tmp_path.read_text(encoding="utf-8", errors="replace")

        if contenido_antes == contenido_despues or total_arreglos == 0:
            cons.print(f"[dim]• {path_arch.name}: Sin cambios necesarios.[/dim]")
            resultados[str(path_arch)] = 0
            continue

        # Generar diff unificado
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
            resp = Prompt.ask(
                f"¿Aplicar estas correcciones a [cyan]{path_arch.name}[/cyan]?",
                choices=["y", "n", "q", "s"],
                default="y",
                console=cons,
            )
            if resp == "q":
                cons.print("[red]⏹ Autofix interactivo cancelado por el usuario.[/red]")
                break
            elif resp not in ("y", "s"):
                cons.print(f"[yellow]• Omitido:[/yellow] {path_arch.name}")
                resultados[str(path_arch)] = 0
                continue

        path_arch.write_text(contenido_despues, encoding="utf-8")
        resultados[str(path_arch)] = total_arreglos
        cons.print(f"[bold green]✓ Corrección aplicada a:[/bold green] [cyan]{path_arch}[/cyan]")

    return resultados
