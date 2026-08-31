"""Diagnóstico de herramientas del entorno para GAFF."""

from __future__ import annotations

import shutil
import subprocess
from typing import Dict, Any, Optional

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


def ejecutar_diagnostico_doctor(console: Optional[Console] = None) -> bool:
    cons = console or Console()
    herramientas = [
        ("clang-format", "Formateador automático institucional", False, "sudo apt install clang-format"),
        ("git", "Control de versiones para instalación de pre-commit hooks", True, "sudo apt install git"),
        ("gcc", "Compilador GNU C para verificación de sintaxis", True, "sudo apt install build-essential"),
    ]
    
    tabla = Table(title="🏥 Diagnóstico del Entorno de GAFF (doctor)", border_style="cyan")
    tabla.add_column("Herramienta", style="bold white")
    tabla.add_column("Estado", justify="center")
    tabla.add_column("Versión / Ruta", style="dim")
    tabla.add_column("Propósito / Acción sugerida", style="yellow")
    
    todo_ok = True
    for cmd, desc, obligatorio, fix in herramientas:
        info = chequear_herramienta(cmd)
        if info["disponible"]:
            estado = "[bold green]✓ OK[/bold green]"
            detalles = f"{info['version']} ([cyan]{info['ruta']}[/cyan])"
            accion = desc
        else:
            if obligatorio:
                estado = "[bold red]✗ Faltante[/bold red]"
                todo_ok = False
            else:
                estado = "[yellow]! Opcional[/yellow]"
            detalles = "[dim]No encontrado en $PATH[/dim]"
            accion = f"{desc} ↳ {fix}"
        tabla.add_row(cmd, estado, detalles, accion)
        
    cons.print(tabla)
    return todo_ok
