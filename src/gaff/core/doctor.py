"""Diagnóstico de herramientas del entorno para GAFF."""

from __future__ import annotations

import shutil
import subprocess
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.table import Table


def chequear_herramienta(comando: str, args_version: str = "--version") -> Dict[str, Any]:
    path = shutil.which(comando)
    if not path:
        return {"disponible": False, "version": None, "ruta": None}
    try:
        res = subprocess.run([comando, args_version], capture_output=True, text=True, timeout=3)
        salida = (res.stdout or res.stderr).strip().splitlines()
        version = salida[0] if salida else "Detectada"
    except Exception:
        version = "Detectada"
    return {"disponible": True, "version": version, "ruta": path}


HERRAMIENTAS = [
    ("clang-format", "Formateador automático institucional", False, "sudo apt install clang-format"),
    ("git", "Control de versiones para instalación de pre-commit hooks", True, "sudo apt install git"),
    ("gcc", "Compilador GNU C para verificación de sintaxis", True, "sudo apt install build-essential"),
]


def diagnosticar() -> List[Dict[str, Any]]:
    """Estado de cada herramienta externa (sin imprimir nada)."""
    chequeos = []
    for cmd, desc, obligatorio, fix in HERRAMIENTAS:
        info = chequear_herramienta(cmd)
        chequeos.append({
            "nombre": cmd,
            "requerido": obligatorio,
            "ok": info["disponible"],
            "detalle": f"{info['version']} ({info['ruta']})" if info["disponible"] else "No encontrado en $PATH",
            "proposito": desc,
            "sugerencia": "" if info["disponible"] else fix,
        })
    return chequeos


def informe_json(chequeos: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Sobre JSON común de `doctor --json` (schema_version 1.0.0)."""
    from gaff import __version__

    return {
        "schema_version": "1.0.0",
        "herramienta": "gaff",
        "version": __version__,
        "ok": all(c["ok"] for c in chequeos if c["requerido"]),
        "chequeos": chequeos,
    }


def ejecutar_diagnostico_doctor(console: Optional[Console] = None) -> bool:
    cons = console or Console()
    tabla = Table(title="🏥 Diagnóstico del Entorno de GAFF (doctor)", border_style="cyan")
    tabla.add_column("Herramienta", style="bold white")
    tabla.add_column("Estado", justify="center")
    tabla.add_column("Versión / Ruta", style="dim")
    tabla.add_column("Propósito / Acción sugerida", style="yellow")

    todo_ok = True
    for chequeo in diagnosticar():
        if chequeo["ok"]:
            estado = "[bold green]✓ OK[/bold green]"
            detalles = chequeo["detalle"]
            accion = chequeo["proposito"]
        else:
            if chequeo["requerido"]:
                estado = "[bold red]✗ Faltante[/bold red]"
                todo_ok = False
            else:
                estado = "[yellow]! Opcional[/yellow]"
            detalles = "[dim]No encontrado en $PATH[/dim]"
            accion = f"{chequeo['proposito']} ↳ {chequeo['sugerencia']}"
        tabla.add_row(chequeo["nombre"], estado, detalles, accion)

    cons.print(tabla)
    return todo_ok
