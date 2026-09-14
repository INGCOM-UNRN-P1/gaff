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
from gaff.core.rules import (
    CATALOGO_REGLAS,
    MAPA_INVERSO,
    MAPA_RENUMERACION,
    normalizar_codigo,
    obtener_regla,
)


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
    """Normaliza el conjunto de códigos de regla a excluir (tolera variantes con/sin 'h' y renumeradas)."""
    excluidas_norm: Set[str] = set()
    if reglas_excluidas:
        for r in reglas_excluidas:
            r_low = str(r).strip().lower()
            excluidas_norm.add(r_low)
            if r_low.startswith("0x") and not r_low.endswith("h"):
                excluidas_norm.add(r_low + "h")
            elif r_low.startswith("0x") and r_low.endswith("h"):
                excluidas_norm.add(r_low[:-1])

            cod_norm = normalizar_codigo(r).lower()
            excluidas_norm.add(cod_norm)
            if cod_norm.endswith("h"):
                excluidas_norm.add(cod_norm[:-1])

            cod_ant = MAPA_INVERSO.get(cod_norm, "").lower()
            if cod_ant:
                excluidas_norm.add(cod_ant)
                if cod_ant.endswith("h"):
                    excluidas_norm.add(cod_ant[:-1])

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
            cod_norm = normalizar_codigo(r).lower()
            reglas_norm.add(cod_norm)
            if cod_norm.endswith("h"):
                reglas_norm.add(cod_norm[:-1])
            cod_ant = MAPA_INVERSO.get(cod_norm, "").lower()
            if cod_ant:
                reglas_norm.add(cod_ant)
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
        cod_nuevo = MAPA_RENUMERACION.get(codigo_hex, MAPA_RENUMERACION.get(cod_low, "")).lower()
        cod_ant = MAPA_INVERSO.get(codigo_hex, MAPA_INVERSO.get(cod_low, "")).lower()

        candidatos = [c for c in (cod_low, cod_nuevo, cod_ant) if c]

        for c in candidatos:
            if c in self.excluidas_norm:
                return False
            if c.endswith("h") and c[:-1] in self.excluidas_norm:
                return False
            if not c.endswith("h") and (c + "h") in self.excluidas_norm:
                return False

        for c in candidatos:
            if c in self.reglas_norm:
                return True
            if c.endswith("h") and c[:-1] in self.reglas_norm:
                return True
            if not c.endswith("h") and (c + "h") in self.reglas_norm:
                return True

        return False

    def regla_info(self, codigo_hex: str) -> Tuple[RuleCode, str]:
        """Retorna el código tipado canónico nuevo y el título de una regla del catálogo."""
        cod_canonico = normalizar_codigo(codigo_hex)
        info = obtener_regla(codigo_hex) or CATALOGO_REGLAS.get(cod_canonico, {})
        titulo = info.get("titulo", f"Regla {cod_canonico}")
        cod_ant = info.get("codigo_anterior", MAPA_INVERSO.get(cod_canonico, ""))
        alias = info.get("alias", f"GAFF_{cod_canonico}")
        return RuleCode(cod_canonico, alias=alias, codigo_anterior=cod_ant), titulo

    def nueva_violacion(self, **kwargs) -> ViolacionRegla:
        """Construye una violación asociada al archivo del contexto."""
        kwargs.setdefault("archivo", self.ruta)
        return ViolacionRegla(**kwargs)
