"""CLI de GAFF — Linter pedagógico de estilo arquitectónico y convenciones de cátedra."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from gaff import __version__
from gaff.core.linter import ejecutar_linter
from gaff.core.rules import CATALOGO_REGLAS

console = Console()
err_console = Console(stderr=True)

app = typer.Typer(
    name="gaff",
    help="📏 GAFF — Linter pedagógico de estilo arquitectónico y convenciones obligatorias de cátedra con autofix.",
    add_completion=True,
    no_args_is_help=True,
)


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"[bold cyan]GAFF[/bold cyan] versión [bold]{__version__}[/bold]")
        raise typer.Exit(code=0)


@app.callback()
def main_callback(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Muestra la versión de GAFF.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    pass


@app.command("check")
def check_cmd(
    rutas: List[Path] = typer.Argument(..., help="Archivos C/H o directorios a analizar."),
    fix: bool = typer.Option(False, "--fix", "-f", help="Aplica automáticamente correcciones en reglas autofixables."),
    rules: Optional[str] = typer.Option(None, "--rules", "-r", help="Lista de códigos de regla separados por comas (ej: 'GAFF001,GAFF005')."),
    json_output: bool = typer.Option(False, "--json", help="Emitir reporte estructurado en JSON."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Ocultar advertencias y solo mostrar errores críticos."),
) -> None:
    """Audita archivos de código C comprobando las reglas de estilo y arquitectura de la cátedra."""
    reglas_set = set(r.strip().upper() for r in rules.split(",") if r.strip()) if rules else None
    reporte = ejecutar_linter(rutas, fix=fix, reglas_habilitadas=reglas_set)

    if json_output:
        print(json.dumps(reporte.to_dict(), indent=2, ensure_ascii=False))
        raise typer.Exit(code=0 if reporte.ok else 1)

    if reporte.ok:
        msg = f"[green]✓ Todos los archivos ({len(reporte.archivos)}) cumplen con las reglas de estilo de la cátedra.[/green]"
        if fix and reporte.total_arreglos > 0:
            msg += f"\n[dim]Se aplicaron {reporte.total_arreglos} correcciones automáticas.[/dim]"
        console.print(Panel(msg, title="GAFF Linting OK", border_style="green"))
        raise typer.Exit(code=0)

    # Mostrar violaciones
    console.print(f"\n[bold red]⚠️ Se encontraron {reporte.total_violaciones} violaciones de estilo:[/bold red]\n")

    tabla = Table(title="Detalle de Violaciones de Estilo")
    tabla.add_column("Ubicación", style="cyan")
    tabla.add_column("Regla", justify="center", style="bold yellow")
    tabla.add_column("Mensaje")
    tabla.add_column("Sugerencia", style="dim")
    tabla.add_column("Fix", justify="center")

    for rep_arch in reporte.archivos:
        for v in rep_arch.violaciones:
            ubicacion = f"{rep_arch.archivo.name}:{v.linea}:{v.columna}"
            fix_str = "[green]✓ auto[/green]" if v.es_autofixable else "[dim]manual[/dim]"
            tabla.add_row(ubicacion, v.codigo, v.mensaje, v.sugerencia, fix_str)

    console.print(tabla)

    if fix and reporte.total_arreglos > 0:
        console.print(f"\n[green]✓ Se aplicaron {reporte.total_arreglos} correcciones automáticas.[/green]")
    elif not fix and any(v.es_autofixable for a in reporte.archivos for v in a.violaciones):
        console.print("\n[dim]💡 Ejecutá 'gaff fix <archivos>' o agregá '--fix' para corregir automáticamente los problemas marcados con '✓ auto'.[/dim]")

    raise typer.Exit(code=1)


@app.command("fix")
def fix_cmd(
    rutas: List[Path] = typer.Argument(..., help="Archivos C/H o directorios a corregir automáticamente."),
    rules: Optional[str] = typer.Option(None, "--rules", "-r", help="Reglas a aplicar."),
) -> None:
    """Aplica correcciones automáticas de estilo directamente sobre los archivos."""
    reglas_set = set(r.strip().upper() for r in rules.split(",") if r.strip()) if rules else None
    reporte = ejecutar_linter(rutas, fix=True, reglas_habilitadas=reglas_set)

    if reporte.total_arreglos > 0:
        console.print(f"[green]✓ Se aplicaron {reporte.total_arreglos} correcciones automáticas en {len(reporte.archivos)} archivo(s).[/green]")
    else:
        console.print("[dim]No se requirieron correcciones automáticas.[/dim]")

    if not reporte.ok:
        console.print(f"[yellow]Aún quedan {reporte.total_violaciones} violaciones que requieren corrección manual. Ejecutá 'gaff check' para verlas.[/yellow]")


@app.command("rules")
def rules_cmd() -> None:
    """Lista todas las reglas de estilo y arquitectura del catálogo de GAFF."""
    tabla = Table(title=f"Catálogo de Reglas de Cátedra GAFF ({len(CATALOGO_REGLAS)} reglas)")
    tabla.add_column("Código", style="bold cyan", justify="center")
    tabla.add_column("Título", style="bold")
    tabla.add_column("Descripción")
    tabla.add_column("Autofix", justify="center")

    for cod, info in sorted(CATALOGO_REGLAS.items()):
        fix_str = "[green]Sí[/green]" if info["autofix"] == "Sí" else "[dim]No[/dim]"
        tabla.add_row(cod, info["titulo"], info["descripcion"], fix_str)

    console.print(tabla)


@app.command("explain")
def explain_cmd(
    codigo: str = typer.Argument(..., help="Código de la regla a explicar (ej: 'GAFF001')."),
) -> None:
    """Explica en detalle una regla de cátedra con ejemplos de código correctos e incorrectos."""
    cod = codigo.strip().upper()
    if cod not in CATALOGO_REGLAS:
        err_console.print(f"[red]Error:[/red] La regla '{cod}' no existe en el catálogo de GAFF.")
        raise typer.Exit(code=2)

    info = CATALOGO_REGLAS[cod]
    cuerpo = (
        f"[bold]{info['titulo']}[/bold]\n\n"
        f"{info['descripcion']}\n\n"
        f"[bold green]✓ Ejemplo Correcto:[/bold green]\n```c\n{info['ejemplo_correcto']}\n```\n\n"
        f"[bold red]✗ Ejemplo Incorrecto:[/bold red]\n```c\n{info['ejemplo_incorrecto']}\n```\n\n"
        f"[dim]Capacidad de Autofix: {info['autofix']}[/dim]"
    )
    console.print(Panel(cuerpo, title=f"📘 Regla {cod}", border_style="cyan"))


def main() -> None:
    app()


if __name__ == "__main__":
    main()
