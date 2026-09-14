"""Contexto de análisis compartido para el motor de reglas de GAFF.

Centraliza las derivaciones de un archivo fuente C (líneas crudas, sin
comentarios y sin literales) junto con el estado de activación de reglas,
de modo que cada regla consuma la misma información precalculada en lugar
de re-derivarla por su cuenta.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set, Tuple

from gaff.core.models import RuleCode, ViolacionRegla
from gaff.core.rules import CATALOGO_REGLAS


def eliminar_comentarios(texto: str) -> str:
    """Reemplaza comentarios de bloque y de línea por espacios sin alterar líneas/columnas."""
    def replacer(match):
        s = match.group(0)
        if s.startswith("/"):
            return "".join("\n" if c == "\n" else " " for c in s)
        return s

    pattern = re.compile(
        r"//.*?$|/\*.*?\*/|'(?:\\.|[^\\'])*'|\"(?:\\.|[^\\\"])*\"",
        re.DOTALL | re.MULTILINE,
    )
    return pattern.sub(replacer, texto)


def enmascarar_literales(texto: str) -> str:
    """Reemplaza literales de cadena y carácter por espacios preservando líneas/columnas."""
    pattern = re.compile(r"'(?:\\.|[^\\'])*'|\"(?:\\.|[^\\\"])*\"", re.DOTALL)
    return pattern.sub(lambda m: "".join("\n" if c == "\n" else " " for c in m.group(0)), texto)


def normalizar_exclusiones(reglas_excluidas: Optional[Set[str]]) -> Set[str]:
    """Normaliza el conjunto de códigos de regla a excluir (tolera variantes con/sin 'h')."""
    excluidas_norm: Set[str] = set()
    if reglas_excluidas:
        for r in reglas_excluidas:
            r_low = str(r).strip().lower()
            excluidas_norm.add(r_low)
            if r_low.startswith("0x") and not r_low.endswith("h"):
                excluidas_norm.add(r_low + "h")
            elif r_low.startswith("0x") and r_low.endswith("h"):
                excluidas_norm.add(r_low[:-1])
            if r in CATALOGO_REGLAS:
                c = CATALOGO_REGLAS[r].get("codigo", "").lower()
                excluidas_norm.add(c)
                if c.endswith("h"):
                    excluidas_norm.add(c[:-1])
    return excluidas_norm


def normalizar_activas(
    reglas_habilitadas: Optional[Set[str]],
    excluidas_norm: Set[str],
) -> Set[str]:
    """Determina el conjunto de reglas activas.

    Por defecto (modo canónico institucional) TODAS las reglas del catálogo
    quedan activas excepto las excluidas. Si se provee ``reglas_habilitadas``,
    se interpreta como filtro de inclusión retrocompatible.
    """
    if reglas_habilitadas is not None:
        reglas_norm: Set[str] = set()
        for r in reglas_habilitadas:
            r_low = str(r).strip().lower()
            reglas_norm.add(r_low)
            if r_low.startswith("0x") and not r_low.endswith("h"):
                reglas_norm.add(r_low + "h")
            if r in CATALOGO_REGLAS:
                reglas_norm.add(CATALOGO_REGLAS[r].get("codigo", "").lower())
        return reglas_norm - excluidas_norm
    return {k.lower() for k in CATALOGO_REGLAS.keys()} - excluidas_norm


@dataclass
class ContextoAnalisis:
    """Datos derivados y estado de activación compartidos por todas las reglas.

    Se construye una única vez por archivo y se pasa a cada familia de reglas,
    evitando que cada verificación re-derive líneas, comentarios enmascarados
    o literales por su cuenta.
    """

    ruta: Path
    contenido_original: str
    lineas: List[str]
    codigo_sin_comentarios: str
    lineas_sin_comentarios: List[str]
    codigo_sin_cadenas: str
    lineas_sin_cadenas: List[str]
    es_header: bool
    excluidas_norm: Set[str] = field(default_factory=set)
    reglas_norm: Set[str] = field(default_factory=set)

    def esta_activa(self, codigo_hex: str) -> bool:
        """Indica si una regla debe evaluarse según exclusiones y filtro activo."""
        cod_low = codigo_hex.lower()
        if cod_low in self.excluidas_norm:
            return False
        if cod_low.endswith("h") and cod_low[:-1] in self.excluidas_norm:
            return False
        if not cod_low.endswith("h") and (cod_low + "h") in self.excluidas_norm:
            return False
        return cod_low in self.reglas_norm

    def regla_info(self, codigo_hex: str) -> Tuple[RuleCode, str]:
        """Retorna el código tipado y el título canónico de una regla del catálogo."""
        info = CATALOGO_REGLAS.get(codigo_hex, {})
        titulo = info.get("titulo", f"Regla {codigo_hex}")
        return RuleCode(codigo_hex), titulo

    def nueva_violacion(self, **kwargs) -> ViolacionRegla:
        """Construye una violación asociada al archivo del contexto."""
        kwargs.setdefault("archivo", self.ruta)
        return ViolacionRegla(**kwargs)
