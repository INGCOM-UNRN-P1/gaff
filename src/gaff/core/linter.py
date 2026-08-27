"""Motor de análisis estático y autofix para GAFF."""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional, Set

from gaff.core.models import ReporteArchivo, ReporteLinting, ViolacionRegla
from gaff.core.rules import CATALOGO_REGLAS


def _eliminar_comentarios(texto: str) -> str:
    """Reemplaza comentarios de bloque y de línea por espacios para no alterar líneas/columnas."""
    def replacer(match):
        s = match.group(0)
        if s.startswith("/"):
            # Reemplazar caracteres preservando saltos de línea
            return "".join("\n" if c == "\n" else " " for c in s)
        return s

    pattern = re.compile(
        r'//.*?$|/\*.*?\*/|\'(?:\\.|[^\\\'])*\'|"(?:\\.|[^\\"])*"',
        re.DOTALL | re.MULTILINE,
    )
    return re.sub(pattern, replacer, texto)


def analizar_archivo(
    ruta: Path,
    reglas_habilitadas: Optional[Set[str]] = None,
) -> List[ViolacionRegla]:
    """Analiza un archivo C o H y retorna la lista de violaciones encontradas."""
    if not ruta.is_file():
        return []

    reglas = reglas_habilitadas or set(CATALOGO_REGLAS.keys())
    violaciones: List[ViolacionRegla] = []

    try:
        contenido_original = ruta.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            contenido_original = ruta.read_text(encoding="latin-1")
        except Exception:
            return []

    lineas = contenido_original.splitlines()
    codigo_sin_comentarios = _eliminar_comentarios(contenido_original)
    lineas_sin_comentarios = codigo_sin_comentarios.splitlines()

    es_header = ruta.suffix.lower() in (".h", ".hpp")

    # GAFF005: Guardas de inclusión en cabeceras (.h)
    if "GAFF005" in reglas and es_header:
        tiene_pragma = "#pragma once" in contenido_original
        tiene_ifndef = bool(re.search(r"#ifndef\s+\w+", contenido_original) and re.search(r"#define\s+\w+", contenido_original))
        if not (tiene_pragma or tiene_ifndef):
            violaciones.append(ViolacionRegla(
                codigo="GAFF005",
                titulo=CATALOGO_REGLAS["GAFF005"]["titulo"],
                archivo=ruta,
                linea=1,
                columna=1,
                mensaje="El archivo de cabecera no cuenta con guardas de inclusión (#ifndef / #define o #pragma once).",
                sugerencia=f"Agregá guardas de preprocesador al inicio y final del archivo:\n#ifndef {ruta.stem.upper()}_H\n#define {ruta.stem.upper()}_H\n...\n#endif",
                es_autofixable=True,
            ))

    # GAFF008: Prohibición de goto
    if "GAFF008" in reglas:
        for idx, linea in enumerate(lineas_sin_comentarios, 1):
            m_goto = re.search(r"\bgoto\s+\w+", linea)
            if m_goto:
                violaciones.append(ViolacionRegla(
                    codigo="GAFF008",
                    titulo=CATALOGO_REGLAS["GAFF008"]["titulo"],
                    archivo=ruta,
                    linea=idx,
                    columna=m_goto.start() + 1,
                    mensaje="Uso de la sentencia 'goto' detectado.",
                    sugerencia="Reemplazá 'goto' por estructuras de control estructuradas (bucles, retornos directos).",
                    codigo_linea=lineas[idx - 1],
                    es_autofixable=False,
                ))

    # GAFF007: Espaciado en palabras clave (if, for, while, switch)
    if "GAFF007" in reglas:
        re_kw = re.compile(r"\b(if|for|while|switch)\(")
        for idx, linea in enumerate(lineas_sin_comentarios, 1):
            m_kw = re_kw.search(linea)
            if m_kw:
                kw = m_kw.group(1)
                violaciones.append(ViolacionRegla(
                    codigo="GAFF007",
                    titulo=CATALOGO_REGLAS["GAFF007"]["titulo"],
                    archivo=ruta,
                    linea=idx,
                    columna=m_kw.start() + 1,
                    mensaje=f"Falta espacio entre palabra clave '{kw}' y el paréntesis de apertura.",
                    sugerencia=f"Escribí '{kw} (' en lugar de '{kw}('",
                    codigo_linea=lineas[idx - 1],
                    es_autofixable=True,
                ))

    # GAFF009: Longitud de línea (> 100 chars)
    if "GAFF009" in reglas:
        for idx, linea in enumerate(lineas, 1):
            if len(linea) > 100:
                violaciones.append(ViolacionRegla(
                    codigo="GAFF009",
                    titulo=CATALOGO_REGLAS["GAFF009"]["titulo"],
                    archivo=ruta,
                    linea=idx,
                    columna=101,
                    mensaje=f"Línea de {len(linea)} caracteres excede el límite máximo de 100.",
                    sugerencia="Dividí la instrucción o llamada en múltiples líneas identadas.",
                    codigo_linea=linea[:80] + "...",
                    es_autofixable=False,
                ))

    # GAFF010: Espacios finales y mezcla de tabuladores
    if "GAFF010" in reglas:
        for idx, linea in enumerate(lineas, 1):
            if linea.endswith(" ") or linea.endswith("\t"):
                violaciones.append(ViolacionRegla(
                    codigo="GAFF010",
                    titulo=CATALOGO_REGLAS["GAFF010"]["titulo"],
                    archivo=ruta,
                    linea=idx,
                    columna=len(linea),
                    mensaje="Espacios en blanco sobrantes al final de la línea (trailing whitespace).",
                    sugerencia="Eliminá los espacios al final de la línea.",
                    codigo_linea=linea,
                    es_autofixable=True,
                ))
            elif "\t" in linea:
                violaciones.append(ViolacionRegla(
                    codigo="GAFF010",
                    titulo=CATALOGO_REGLAS["GAFF010"]["titulo"],
                    archivo=ruta,
                    linea=idx,
                    columna=linea.find("\t") + 1,
                    mensaje="Uso de tabuladores duros (\\t) detectado.",
                    sugerencia="Reemplazá tabuladores por 4 espacios.",
                    codigo_linea=linea,
                    es_autofixable=True,
                ))

    # GAFF001: CamelCase en funciones o variables
    if "GAFF001" in reglas:
        re_camel = re.compile(r"\b(?:int|void|char|float|double|size_t|bool|\w+_t|t_\w+)\s+([a-z]+[A-Z]\w*)\s*\(")
        for idx, linea in enumerate(lineas_sin_comentarios, 1):
            m_fn = re_camel.search(linea)
            if m_fn:
                fn_name = m_fn.group(1)
                violaciones.append(ViolacionRegla(
                    codigo="GAFF001",
                    titulo=CATALOGO_REGLAS["GAFF001"]["titulo"],
                    archivo=ruta,
                    linea=idx,
                    columna=m_fn.start(1) + 1,
                    mensaje=f"Nombre de función '{fn_name}' escrito en camelCase.",
                    sugerencia="Usá snake_case (todo en minúsculas con guiones bajos).",
                    codigo_linea=lineas[idx - 1],
                    es_autofixable=False,
                ))

    # GAFF002: Nomenclatura de typedef
    if "GAFF002" in reglas:
        re_typedef = re.compile(r"\btypedef\s+(?:struct|enum|union)\s*(?:\w*\s*\{[^}]*\}|\w+)\s+(\w+)\s*;", re.DOTALL)
        for m in re_typedef.finditer(codigo_sin_comentarios):
            tipo_name = m.group(1)
            if not (tipo_name.startswith("t_") or tipo_name.endswith("_t") or tipo_name.startswith("T_")):
                # Calcular número de línea
                line_no = codigo_sin_comentarios[:m.start(1)].count("\n") + 1
                violaciones.append(ViolacionRegla(
                    codigo="GAFF002",
                    titulo=CATALOGO_REGLAS["GAFF002"]["titulo"],
                    archivo=ruta,
                    linea=line_no,
                    columna=1,
                    mensaje=f"El tipo definido '{tipo_name}' no utiliza el prefijo 't_' ni el sufijo '_t'.",
                    sugerencia=f"Renombralo como 't_{tipo_name.lower()}' o '{tipo_name.lower()}_t'.",
                    es_autofixable=False,
                ))

    # GAFF004: Longitud máxima de función (> 50 líneas)
    if "GAFF004" in reglas:
        re_fn_start = re.compile(r"^\s*(?:[a-zA-Z0-9_*]+\s+)+([a-zA-Z0-9_]+)\s*\([^)]*\)\s*\{", re.MULTILINE)
        for m in re_fn_start.finditer(codigo_sin_comentarios):
            fn_name = m.group(1)
            start_pos = m.end() - 1
            line_start = codigo_sin_comentarios[:m.start()].count("\n") + 1

            # Contar llaves balanceadas
            brace_count = 0
            end_pos = start_pos
            for i in range(start_pos, len(codigo_sin_comentarios)):
                if codigo_sin_comentarios[i] == '{':
                    brace_count += 1
                elif codigo_sin_comentarios[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_pos = i
                        break
            line_end = codigo_sin_comentarios[:end_pos].count("\n") + 1
            total_lines = line_end - line_start + 1
            if total_lines > 50:
                violaciones.append(ViolacionRegla(
                    codigo="GAFF004",
                    titulo=CATALOGO_REGLAS["GAFF004"]["titulo"],
                    archivo=ruta,
                    linea=line_start,
                    columna=1,
                    mensaje=f"Función '{fn_name}' tiene {total_lines} líneas (máximo permitido: 50).",
                    sugerencia="Modularizá la función dividiéndola en funciones auxiliares.",
                    es_autofixable=False,
                ))

    violaciones.sort(key=lambda v: (v.linea, v.columna))
    return violaciones


def aplicar_autofix_archivo(ruta: Path) -> int:
    """Aplica correcciones automáticas sobre reglas autofixables (GAFF005, GAFF007, GAFF010)."""
    if not ruta.is_file():
        return 0

    try:
        contenido = ruta.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        contenido = ruta.read_text(encoding="latin-1")

    arreglos = 0
    lineas = contenido.splitlines()
    nuevas_lineas = []

    # Fix GAFF007 y GAFF010 línea por línea
    re_kw = re.compile(r"\b(if|for|while|switch)\(")
    for linea in lineas:
        orig = linea
        # GAFF010: tabs to spaces y strip trailing
        linea = linea.replace("\t", "    ").rstrip()
        # GAFF007: keywords spacing
        linea = re_kw.sub(r"\1 (", linea)

        if linea != orig:
            arreglos += 1
        nuevas_lineas.append(linea)

    contenido_mod = "\n".join(nuevas_lineas) + "\n"

    # Fix GAFF005: Guardas de inclusión en .h
    if ruta.suffix.lower() in (".h", ".hpp"):
        tiene_pragma = "#pragma once" in contenido_mod
        tiene_ifndef = bool(re.search(r"#ifndef\s+\w+", contenido_mod) and re.search(r"#define\s+\w+", contenido_mod))
        if not (tiene_pragma or tiene_ifndef):
            guard_name = f"{ruta.stem.upper()}_H"
            contenido_mod = f"#ifndef {guard_name}\n#define {guard_name}\n\n{contenido_mod.strip()}\n\n#endif // {guard_name}\n"
            arreglos += 1

    if arreglos > 0:
        ruta.write_text(contenido_mod, encoding="utf-8")

    return arreglos


def ejecutar_linter(
    rutas: List[Path],
    fix: bool = False,
    reglas_habilitadas: Optional[Set[str]] = None,
) -> ReporteLinting:
    """Ejecuta el linter sobre un conjunto de archivos o directorios."""
    archivos_objetivo: Set[Path] = set()
    for r in rutas:
        p = Path(r)
        if p.is_file() and p.suffix.lower() in (".c", ".h", ".cpp", ".hpp"):
            archivos_objetivo.add(p)
        elif p.is_dir():
            for sub_p in p.rglob("*"):
                if sub_p.is_file() and sub_p.suffix.lower() in (".c", ".h", ".cpp", ".hpp"):
                    archivos_objetivo.add(sub_p)

    reportes: List[ReporteArchivo] = []
    for arch in sorted(archivos_objetivo):
        arreglos = 0
        if fix:
            arreglos = aplicar_autofix_archivo(arch)
        viols = analizar_archivo(arch, reglas_habilitadas=reglas_habilitadas)
        reportes.append(ReporteArchivo(
            archivo=arch,
            violaciones=viols,
            arreglos_aplicados=arreglos,
        ))

    return ReporteLinting(archivos=reportes)
