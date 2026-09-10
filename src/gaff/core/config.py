"""Gestor de configuración local granular (.gaffrc.yaml, gaff.toml, pyproject.toml) para GAFF.

La filosofía de configuración de GAFF se basa en EXCLUSIÓN: por defecto todas las
reglas pedagógicas de la cátedra se aplican obligatoriamente, y solo se configuran
las reglas que explícitamente se desean desactivar/ignorar.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import yaml

try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        tomllib = None  # type: ignore


DEFAULT_CONFIG: Dict[str, Any] = {
    "max_line_length": 80,
    "max_file_lines": 500,
    "max_function_lines": 40,
    "max_nesting_depth": 3,
    "disallow_tabs": True,
    "enforce_allman": True,
    "excluded_rules": [],
    "disabled_rules": [],
}


def obtener_reglas_excluidas(config: Dict[str, Any]) -> Set[str]:
    """Extrae el conjunto normalizado de códigos de regla a excluir de un diccionario de configuración."""
    excluidas: Set[str] = set()

    for clave in (
        "excluded_rules",
        "disabled_rules",
        "exclude",
        "ignore",
        "excluir_reglas",
        "reglas_excluidas",
        "ignore_rules",
    ):
        valores = config.get(clave)
        if isinstance(valores, (list, set, tuple)):
            for v in valores:
                if isinstance(v, str) and v.strip():
                    excluidas.add(v.strip())
        elif isinstance(valores, str) and valores.strip():
            for v in valores.split(","):
                if v.strip():
                    excluidas.add(v.strip())

    return excluidas


def cargar_configuracion_gaff(directorio: Optional[Path] = None) -> Dict[str, Any]:
    """Busca y carga recursivamente la configuración de exclusiones desde .gaffrc.yaml, gaff.yaml o pyproject.toml."""
    dir_actual = Path(directorio or ".").resolve()
    config = dict(DEFAULT_CONFIG)

    candidatos_yaml = [
        dir_actual / ".gaffrc.yaml",
        dir_actual / ".gaffrc.yml",
        dir_actual / "gaff.yaml",
        dir_actual / "gaff.yml",
        dir_actual / ".gaff.yaml",
    ]

    candidatos_json = [
        dir_actual / ".gaffrc.json",
        dir_actual / "gaff.json",
        dir_actual / ".gaff.json",
        dir_actual / ".gaffrc",
    ]

    candidatos_toml = [
        dir_actual / "gaff.toml",
        dir_actual / ".gaff.toml",
        dir_actual / "pyproject.toml",
    ]

    # 1. Probar archivos YAML
    for cand in candidatos_yaml:
        if cand.is_file():
            try:
                datos = yaml.safe_load(cand.read_text(encoding="utf-8")) or {}
                if isinstance(datos, dict):
                    config.update(datos)
                break
            except Exception:
                pass

    # 2. Probar archivos JSON
    import json
    for cand in candidatos_json:
        if cand.is_file():
            try:
                datos = json.loads(cand.read_text(encoding="utf-8"))
                if isinstance(datos, dict):
                    config.update(datos)
                break
            except Exception:
                pass

    # 3. Probar archivos TOML si tomllib está disponible
    if tomllib is not None:
        for cand in candidatos_toml:
            if cand.is_file():
                try:
                    toml_data = tomllib.loads(cand.read_text(encoding="utf-8"))
                    datos = toml_data.get("tool", {}).get("gaff", {}) if cand.name == "pyproject.toml" else toml_data
                    if isinstance(datos, dict):
                        config.update(datos)
                    break
                except Exception:
                    pass

    # Asegurar que excluded_rules contenga la consolidación de todas las exclusiones
    excluidas_set = obtener_reglas_excluidas(config)
    config["excluded_rules"] = sorted(list(excluidas_set))
    config["disabled_rules"] = config["excluded_rules"]

    return config


def generar_plantilla_gaffrc_json(
    tp_nombre: str = "TP General",
    catedra: str = "Cátedra de Algoritmos y Programación",
    reglas_excluidas: Optional[List[str]] = None,
    max_line_length: int = 80,
    max_function_lines: int = 40,
) -> Dict[str, Any]:
    """Genera un diccionario estructurado para serializar como .gaffrc.json."""
    return {
        "$schema": "https://raw.githubusercontent.com/unsam/gaff/main/schema/gaffrc.schema.json",
        "catedra": catedra,
        "tp": tp_nombre,
        "version": "1.0",
        "description": f"Configuración pedagógica de estilo GAFF para {tp_nombre} ({catedra})",
        "max_line_length": max_line_length,
        "max_function_lines": max_function_lines,
        "max_file_lines": 500,
        "max_nesting_depth": 3,
        "disallow_tabs": True,
        "enforce_allman": True,
        "excluded_rules": sorted(list(set(reglas_excluidas or []))),
        "disabled_rules": sorted(list(set(reglas_excluidas or []))),
    }

