"""Gestor de configuración local granular (.gaffrc.yaml) para GAFF."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Set
import yaml


DEFAULT_CONFIG: Dict[str, Any] = {
    "max_line_length": 80,
    "max_file_lines": 500,
    "max_nesting_depth": 3,
    "disallow_tabs": True,
    "enforce_allman": True,
    "disabled_rules": [],
    "enabled_rules": [],
}


def cargar_configuracion_gaff(directorio: Optional[Path] = None) -> Dict[str, Any]:
    """Busca y carga recursivamente un archivo .gaffrc.yaml o gaff.yaml."""
    dir_actual = Path(directorio or ".").resolve()
    config = dict(DEFAULT_CONFIG)

    candidatos = [
        dir_actual / ".gaffrc.yaml",
        dir_actual / ".gaffrc.yml",
        dir_actual / "gaff.yaml",
        dir_actual / "gaff.yml",
        dir_actual / ".gaff.yaml",
    ]

    for cand in candidatos:
        if cand.is_file():
            try:
                datos = yaml.safe_load(cand.read_text(encoding="utf-8")) or {}
                if isinstance(datos, dict):
                    config.update(datos)
                break
            except Exception:
                pass

    return config
