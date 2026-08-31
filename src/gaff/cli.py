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


def generar_seccion_markdown(reporte) -> str:
    """Genera una sección Markdown estructurada para fusión con Dredd."""
    lines = ["## Auditoría de Estilo y Convenciones Cátedra (Gaff)\n"]
    lines.append(f"- **Archivos analizados:** {len(reporte.archivos)}")
    lines.append(f"- **Violaciones detectadas:** {reporte.total_violaciones}")
    if reporte.total_arreglos > 0:
        lines.append(f"- **Correcciones automáticas aplicadas:** {reporte.total_arreglos}")
    lines.append("")
    if reporte.ok:
        lines.append("> [!TIP]\n> **Cumplimiento Total:** Todos los archivos cumplen con las directivas de estilo y convenciones arquitectónicas de la cátedra.\n")
    else:
        lines.append("| Archivo | Línea | Regla | Descripción | Sugerencia | Autofix |")
        lines.append("| :--- | :---: | :---: | :--- | :--- | :---: |")
        for rep_arch in reporte.archivos:
            for v in rep_arch.violaciones:
                fix_tag = "✓ Sí" if v.es_autofixable else "No"
                lines.append(f"| `{rep_arch.archivo.name}` | {v.linea} | `{v.codigo}` | {v.mensaje} | {v.sugerencia} | {fix_tag} |")
        lines.append("")
    return "\n".join(lines)


@app.command("check")
def check_cmd(
    rutas: List[Path] = typer.Argument(..., help="Archivos C/H o directorios a analizar."),
    fix: bool = typer.Option(False, "--fix", "-f", help="Aplica automáticamente correcciones en reglas autofixables."),
    rules: Optional[str] = typer.Option(None, "--rules", "-r", help="Lista de códigos de regla separados por comas (ej: 'GAFF001,GAFF005')."),
    json_output: bool = typer.Option(False, "--json", help="Emitir reporte estructurado en JSON."),
    output_md: Optional[Path] = typer.Option(None, "--md", "--output-md", "-o", help="Generar sección de reporte en formato Markdown para fusión en Dredd."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Ocultar advertencias y solo mostrar errores críticos."),
) -> None:
    """Audita archivos de código C comprobando las reglas de estilo y arquitectura de la cátedra."""
    reglas_set = set(r.strip().upper() for r in rules.split(",") if r.strip()) if rules else None
    reporte = ejecutar_linter(rutas, fix=fix, reglas_habilitadas=reglas_set)

    if output_md:
        md_text = generar_seccion_markdown(reporte)
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text(md_text, encoding="utf-8")
        console.print(f"[green]✓ Sección Markdown generada en:[/green] [cyan]{output_md}[/cyan]")
        raise typer.Exit(code=0 if reporte.ok else 1)

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


@app.command("report")
def report_cmd(
    rutas: List[Path] = typer.Argument(..., help="Archivos C/H o directorios a analizar."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Ruta de destino del archivo Markdown."),
    rules: Optional[str] = typer.Option(None, "--rules", "-r", help="Reglas a habilitar."),
) -> None:
    """Genera directamente la sección de reporte Markdown de GAFF para Dredd."""
    reglas_set = set(r.strip().upper() for r in rules.split(",") if r.strip()) if rules else None
    reporte = ejecutar_linter(rutas, fix=False, reglas_habilitadas=reglas_set)
    md_content = generar_seccion_markdown(reporte)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(md_content, encoding="utf-8")
        console.print(f"[green]✓ Reporte Markdown generado en:[/green] [cyan]{output}[/cyan]")
    else:
        print(md_content)


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
    codigo: str = typer.Argument(..., help="Código de la regla a explicar (ej: 'GAFF001' o '0x0001h')."),
) -> None:
    """Explica en detalle una regla de cátedra con ejemplos de código correctos e incorrectos."""
    from gaff.core.rules import obtener_regla

    info = obtener_regla(codigo)
    if not info:
        err_console.print(f"[red]Error:[/red] La regla '{codigo}' no existe en el catálogo de GAFF.")
        raise typer.Exit(code=2)

    cod = info.get("codigo", codigo)
    alias = info.get("alias", "")
    cuerpo = (
        f"[bold]{info['titulo']}[/bold]\n\n"
        f"{info['descripcion']}\n\n"
        f"[bold green]✓ Ejemplo Correcto:[/bold green]\n```c\n{info['ejemplo_correcto']}\n```\n\n"
        f"[bold red]✗ Ejemplo Incorrecto:[/bold red]\n```c\n{info['ejemplo_incorrecto']}\n```\n\n"
        f"[dim]Capacidad de Autofix: {info['autofix']} | Alias: {alias}[/dim]"
    )
    console.print(Panel(cuerpo, title=f"📘 Regla {cod} ({alias})", border_style="cyan"))


CLANG_FORMAT_CATEDRA = """# Configuración canónica de formato para Cátedra de Programación 1 / Algoritmos
BasedOnStyle: LLVM
IndentWidth: 4
UseTab: Never
ColumnLimit: 100
AllowShortIfStatementsOnASingleLine: false
AllowShortLoopsOnASingleLine: false
AllowShortFunctionsOnASingleLine: None
BreakBeforeBraces: Allman
IndentCaseLabels: false
SpaceBeforeParens: ControlStatements
SpacesInParentheses: false
SpacesInSquareBrackets: false
SpaceInEmptyParentheses: false
AlignAfterOpenBracket: Align
AlignConsecutiveDeclarations: false
AlignConsecutiveAssignments: false
PointerAlignment: Right
DerivePointerAlignment: false
SortIncludes: false
"""


@app.command("init-config")
def init_config_cmd(
    target_dir: Path = typer.Option(Path("."), "--dir", "-d", help="Directorio donde generar .clang-format"),
    force: bool = typer.Option(False, "--force", "-f", help="Sobrescribir archivo existente"),
) -> None:
    """Exporta el archivo canónico .clang-format con la configuración de estilo de la cátedra."""
    cfg_file = target_dir / ".clang-format"
    if cfg_file.exists() and not force:
        console.print(f"[yellow]El archivo '{cfg_file}' ya existe. Usá '--force' para sobrescribirlo.[/yellow]")
        raise typer.Exit(code=1)
    cfg_file.write_text(CLANG_FORMAT_CATEDRA, encoding="utf-8")
    console.print(f"[bold green]✓ Archivo de formato .clang-format generado exitosamente en:[/bold green] {cfg_file.resolve()}")


@app.command("fix")
def fix_cmd(
    rutas: List[Path] = typer.Argument(..., help="Archivos C/H o directorios a corregir."),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Previsualiza el diff de cada cambio antes de aplicar."),
) -> None:
    """Aplica correcciones automáticas de estilo con opción de vista previa interactiva."""
    from gaff.core.interactive_fix import ejecutar_autofix_interactivo
    archivos = []
    for r in rutas:
        if r.is_file() and r.suffix in (".c", ".h"):
            archivos.append(r)
        elif r.is_dir():
            archivos.extend(list(r.glob("**/*.c")) + list(r.glob("**/*.h")))

    if not archivos:
        console.print("[yellow]No se encontraron archivos C/H para corregir.[/yellow]")
        raise typer.Exit(code=0)

    res = ejecutar_autofix_interactivo(archivos, auto_confirmar=not interactive, console=console)
    tot = sum(res.values())
    console.print(f"[bold green]✓ Proceso completado: {tot} correcciones automáticas aplicadas en {len(archivos)} archivo(s).[/bold green]")


@app.command("format")
def format_cmd(
    rutas: List[Path] = typer.Argument(..., help="Archivos o directorios a formatear"),
) -> None:
    """Formatea código C/H aplicando las convenciones canónicas de la cátedra."""
    import subprocess
    import shutil
    clang_fmt = shutil.which("clang-format")
    files_to_fmt = []
    for r in rutas:
        if r.is_file() and r.suffix in (".c", ".h"):
            files_to_fmt.append(r)
        elif r.is_dir():
            files_to_fmt.extend(list(r.glob("**/*.c")) + list(r.glob("**/*.h")))

    if not files_to_fmt:
        console.print("[yellow]No se encontraron archivos C/H para formatear.[/yellow]")
        raise typer.Exit(code=0)

    if clang_fmt:
        cmd = [clang_fmt, "-i"] + [str(f) for f in files_to_fmt]
        subprocess.run(cmd, check=False)
        console.print(f"[bold green]✓ {len(files_to_fmt)} archivo(s) formateados con clang-format.[/bold green]")
    else:
        # Fallback a autofix nativo de GAFF
        reporte = ejecutar_linter(files_to_fmt, fix=True)
        console.print(f"[bold green]✓ Formato básico y correcciones de estilo aplicadas ({reporte.total_arreglos} arreglos).[/bold green]")


@app.command("install-hook")
def install_hook_cmd(
    git_dir: Path = typer.Option(Path(".git"), "--git-dir", help="Directorio .git del repositorio"),
) -> None:
    """Instala un hook pre-commit de git para verificar estilo con GAFF antes de commitear."""
    if not git_dir.is_dir():
        err_console.print(f"[red]Error:[/red] No se encontró el directorio git en '{git_dir}'.")
        raise typer.Exit(code=1)

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    pre_commit = hooks_dir / "pre-commit"
    hook_script = """#!/usr/bin/env bash
# Hook pre-commit instalado por GAFF
echo "🔍 Ejecutando auditoría de estilo GAFF..."
if command -v gaff &> /dev/null; then
    gaff check .
    EXIT_CODE=$?
    if [ $EXIT_CODE -ne 0 ]; then
        echo "❌ Falló la verificación de estilo GAFF. Corregí los problemas o ejecutá 'gaff fix .' antes de commitear."
        exit 1
    fi
fi
exit 0
"""
    pre_commit.write_text(hook_script, encoding="utf-8")
    pre_commit.chmod(0o755)
    console.print(f"[bold green]✓ Hook pre-commit instalado exitosamente en:[/bold green] {pre_commit.resolve()}")


@app.command("doctor")
def doctor_cmd() -> None:
    """Verifica dependencias externas de GAFF (clang-format, git, gcc)."""
    from gaff.core.doctor import ejecutar_diagnostico_doctor
    ok = ejecutar_diagnostico_doctor(console=console)
    if not ok:
        raise typer.Exit(code=1)


@app.command("export-rules")
def export_rules_cmd(
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Ruta de destino del archivo Markdown."),
) -> None:
    """Exporta el manual y catálogo oficial de reglas de estilo en formato Markdown."""
    from gaff.core.exporter import generar_guia_estilo_markdown
    md_text = generar_guia_estilo_markdown()
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(md_text, encoding="utf-8")
        console.print(f"[bold green]✓ Guía de estilo exportada exitosamente en:[/bold green] [cyan]{output}[/cyan]")
    else:
        print(md_text)


def main() -> None:
    app()


if __name__ == "__main__":
    main()

