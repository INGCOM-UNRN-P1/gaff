"""Gestor de configuración local granular (.gaffrc.yaml, gaff.toml, pyproject.toml) para GAFF.

La filosofía de configuración de GAFF se basa en EXCLUSIÓN: por defecto todas las
reglas pedagógicas de la cátedra se aplican obligatoriamente, y solo se configuran
las reglas que explícitamente se desean desactivar/ignorar.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set
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
    # Reglas opcionales que se activan (REGLAS_OPCIONALES, por ejemplo 0x3020h).
    "enabled_rules": [],
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


def obtener_reglas_activadas(config: Dict[str, Any]) -> Set[str]:
    """Reglas opcionales que la configuración activa (enabled_rules, reglas_activadas o activar)."""
    activadas: Set[str] = set()
    for clave in ("enabled_rules", "reglas_activadas", "activar"):
        valores = config.get(clave)
        if isinstance(valores, str):
            valores = valores.split(",")
        if isinstance(valores, (list, set, tuple)):
            activadas.update(v.strip() for v in valores if isinstance(v, str) and v.strip())
    return activadas


_ARCHIVOS_GAFF = (
    ".gaffrc.yaml", ".gaffrc.yml", "gaff.yaml", "gaff.yml", ".gaff.yaml",
    ".gaffrc.json", "gaff.json", ".gaff.json", ".gaffrc", "gaff.toml", ".gaff.toml",
)


def _tiene_configuracion(d: Path) -> bool:
    if any((d / n).is_file() for n in _ARCHIVOS_GAFF):
        return True
    pyproject = d / "pyproject.toml"
    if pyproject.is_file() and tomllib is not None:
        try:
            return "gaff" in tomllib.loads(pyproject.read_text(encoding="utf-8")).get("tool", {})
        except Exception:
            return False
    return False


def _hacia_arriba(desde: Path) -> Iterable[Path]:
    """`desde` y sus padres hasta la raíz del repositorio (el primero con .git) o del disco."""
    for d in (desde, *desde.parents):
        yield d
        if (d / ".git").exists():
            return


def directorio_de_configuracion(desde: Optional[Path] = None) -> Path:
    """El directorio cuya configuración de gaff vale para `desde`: el más cercano hacia arriba que
    tenga una (la del TP activo, aunque se analice un archivo de una subcarpeta), sin salir del
    repositorio. Si ninguno tiene, `desde`."""
    inicio = Path(desde or ".").resolve()
    return next((d for d in _hacia_arriba(inicio) if _tiene_configuracion(d)), inicio)


def patrones_de_ripley(desde: Optional[Path] = None) -> List[str]:
    """Las reglas que la actividad no evalúa según su ripley.toml (`[reglas] ignorar`) o su
    .ripleyignore, el más cercano hacia arriba: así gaff solo (al guardar, o en vivo en jonesy)
    filtra lo mismo que `ripley check` en el TP activo. Un patrón es un código, un comodín o
    `gaff:código`; los de otras herramientas (`kaneda:…`) no se aplican."""
    inicio = Path(desde or ".").resolve()
    for d in _hacia_arriba(inicio):
        patrones: List[str] = []
        toml = d / "ripley.toml"
        if toml.is_file() and tomllib is not None:
            try:
                reglas = tomllib.loads(toml.read_text(encoding="utf-8")).get("reglas", {})
                patrones += [str(x) for x in reglas.get("ignorar", []) or []]
            except Exception:  # noqa: BLE001 — un ripley.toml roto lo informa ripley, no este filtro
                pass
        ignore = d / ".ripleyignore"
        if ignore.is_file():
            for linea in ignore.read_text(encoding="utf-8", errors="replace").splitlines():
                linea = linea.split("#", 1)[0].strip()
                if linea:
                    patrones.append(linea)
        if patrones or toml.is_file():
            return [x for x in patrones if ":" not in x or x.lower().startswith("gaff:")]
    return []


def ignorada_por_la_actividad(codigo: str, patrones: List[str]) -> bool:
    """¿El código coincide con algún patrón de `patrones_de_ripley`? Como en ripley, sin el código
    anterior a la renumeración: el viejo 0x0007h es hoy 0x0102h y otra regla se llama 0x0007h."""
    if not patrones:
        return False
    from gaff.core.rules import normalizar_codigo

    nombres = {codigo.lower(), normalizar_codigo(codigo).lower()}
    for patron in patrones:
        p = patron.lower().removeprefix("gaff:")
        if any(fnmatch.fnmatch(n, p) for n in nombres):
            return True
    return False


def cargar_configuracion_gaff(directorio: Optional[Path] = None) -> Dict[str, Any]:
    """Carga la configuración de exclusiones desde .gaffrc.yaml, gaff.yaml, gaff.toml o
    pyproject.toml del directorio más cercano hacia arriba que tenga una (sin salir del
    repositorio, ver `directorio_de_configuracion`)."""
    dir_actual = directorio_de_configuracion(directorio)
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
    config["enabled_rules"] = sorted(obtener_reglas_activadas(config))

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



_SEVERIDADES_VALIDAS = {"error": "ERROR", "advertencia": "ADVERTENCIA", "estilo": "ESTILO", "off": None}


def _claves_de_regla(codigo: str) -> List[str]:
    """Por qué nombres se puede referir una regla en la configuración: su código, su familia
    (`00_formato` o `formato`) y su categoría común (`memoria`, `estilo`…)."""
    from gaff.core.rules import CATALOGO_REGLAS, normalizar_codigo
    from gaff.core.taxonomia import categoria

    cod = normalizar_codigo(codigo)
    familia = CATALOGO_REGLAS.get(cod, {}).get("directorio", "")
    claves = [cod.lower()]
    if familia:
        claves += [familia.lower(), familia.split("_", 1)[-1].lower()]
    claves.append(categoria(cod))
    return claves


def aplicar_severidades_por_actividad(violaciones: List[Any], config: Dict[str, Any]) -> List[Any]:
    """Severidad por actividad (en el TP1 solo formato; en el final, todo).

    - `familias: [formato, nomenclatura]` deja solo las reglas de esas familias;
    - `severidades: {memoria: error, "0x0001h": off}` cambia la severidad de una regla, familia o
      categoría (`error`, `advertencia`, `estilo` u `off` para no informarla). El código exacto
      gana sobre la familia y la familia sobre la categoría.
    """
    familias = {str(f).lower() for f in (config.get("familias") or [])}
    severidades = {str(k).lower(): str(v).lower() for k, v in (config.get("severidades") or {}).items()}
    for valor in severidades.values():
        if valor not in _SEVERIDADES_VALIDAS:
            raise ValueError(f"severidad «{valor}» inválida en la configuración de gaff: usá "
                             f"{', '.join(_SEVERIDADES_VALIDAS)}")
    if not familias and not severidades:
        return violaciones
    resultado = []
    for v in violaciones:
        claves = _claves_de_regla(str(v.codigo))
        if familias and not familias & set(claves[1:3]):
            continue
        cambio = next((severidades[c] for c in claves if c in severidades), None)
        if cambio is not None:
            if _SEVERIDADES_VALIDAS[cambio] is None:
                continue
            v.severidad = _SEVERIDADES_VALIDAS[cambio]
        resultado.append(v)
    return resultado
