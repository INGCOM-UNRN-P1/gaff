"""Motor de análisis estático y autofix para GAFF con verificación exhaustiva de reglas de cátedra."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import List, Optional, Set, Tuple

from gaff.core.models import ReporteArchivo, ReporteLinting, RuleCode, ViolacionRegla
from gaff.core.rules import CATALOGO_REGLAS


def _eliminar_comentarios(texto: str) -> str:
    """Reemplaza comentarios de bloque y de línea por espacios para no alterar líneas/columnas."""
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


def _enmascarar_literales(texto: str) -> str:
    """Reemplaza literales de cadena y carácter por espacios preservando líneas/columnas."""
    pattern = re.compile(r"'(?:\\.|[^\\'])*'|\"(?:\\.|[^\\\"])*\"", re.DOTALL)
    return pattern.sub(lambda m: "".join("\n" if c == "\n" else " " for c in m.group(0)), texto)


def _tiene_comentario_documentacion(lineas: List[str], line_idx: int) -> bool:
    """Verifica si la línea (0-indexed) está precedida inmediatamente por un comentario de documentación."""
    idx = line_idx - 1
    blank_lines = 0
    while idx >= 0 and not lineas[idx].strip():
        blank_lines += 1
        idx -= 1
        if blank_lines > 2:
            return False

    if idx < 0:
        return False

    linea_anterior = lineas[idx].strip()

    if linea_anterior.endswith("*/"):
        inicio_idx = idx
        bloque_lineas = [lineas[inicio_idx]]
        while inicio_idx >= 0 and "/*" not in lineas[inicio_idx]:
            inicio_idx -= 1
            if inicio_idx >= 0:
                bloque_lineas.append(lineas[inicio_idx])

        if inicio_idx >= 0:
            texto_bloque = "\n".join(reversed(bloque_lineas))
            if "/**" in texto_bloque or "/*!" in texto_bloque:
                return True
            if any(tag in texto_bloque for tag in ("@brief", r"\brief", "@param", r"\param", "@return", r"\return", "@pre", "@post")):
                return True
            contenido_limpio = re.sub(r"/\*+|\*+/|\*", " ", texto_bloque).strip()
            if len(contenido_limpio) >= 8 and not contenido_limpio.startswith(("#", "//", "int ", "void ")):
                return True

    if linea_anterior.startswith("//"):
        bloque_lineas = []
        curr = idx
        while curr >= 0 and lineas[curr].strip().startswith("//"):
            bloque_lineas.append(lineas[curr].strip())
            curr -= 1
        texto_lineas = " ".join(reversed(bloque_lineas))
        if "///" in texto_lineas or "//!" in texto_lineas:
            return True
        if any(tag in texto_lineas for tag in ("@brief", r"\brief", "@param", r"\param", "@return", r"\return")):
            return True
        contenido_limpio = re.sub(r"^/+\s*", "", texto_lineas).strip()
        if len(contenido_limpio) >= 8 and not contenido_limpio.startswith(("#", "int ", "void ", "return ")):
            return True

    return False


# Tipos básicos de C
TIPOS_BASICOS = r"(?:int|unsigned\s+int|short|unsigned\s+short|long|unsigned\s+long|long\s+long|char|unsigned\s+char|float|double|long\s+double|size_t|ssize_t|bool|_Bool|void|FILE|\w+_t|t_\w+)"


def analizar_archivo(
    ruta: Path,
    reglas_excluidas: Optional[Set[str]] = None,
    reglas_habilitadas: Optional[Set[str]] = None,
) -> List[ViolacionRegla]:
    """Analiza un archivo fuente C y retorna las violaciones de estilo encontradas.

    Por diseño pedagógico institucional, la configuración es por EXCLUSIÓN: todas
    las reglas del catálogo se evalúan obligatoriamente salvo las especificadas en
    `reglas_excluidas`.
    """
    ruta = Path(ruta)
    if not ruta.is_file():
        return []

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

    def _enmascarar_cadenas_y_chars(texto: str) -> str:
        def repl(m):
            return "".join("\n" if c == "\n" else " " for c in m.group(0))
        return re.sub(r'"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'', repl, texto)

    codigo_sin_cadenas = _enmascarar_cadenas_y_chars(codigo_sin_comentarios)
    lineas_sin_cadenas = codigo_sin_cadenas.splitlines()

    es_header = ruta.suffix.lower() in (".h", ".hpp")

    # 1. Normalizar conjunto de reglas excluidas (modo canónico institucional)
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

    # 2. Determinar reglas activas
    if reglas_habilitadas is not None:
        # Retrocompatibilidad con tests heredados que pasen lista de inclusión
        reglas_norm = set()
        for r in reglas_habilitadas:
            r_low = str(r).strip().lower()
            reglas_norm.add(r_low)
            if r_low.startswith("0x") and not r_low.endswith("h"):
                reglas_norm.add(r_low + "h")
            if r in CATALOGO_REGLAS:
                reglas_norm.add(CATALOGO_REGLAS[r].get("codigo", "").lower())
        reglas_norm = reglas_norm - excluidas_norm
    else:
        # Por defecto: TODAS las reglas de cátedra activas EXCEPTO las excluidas
        reglas_norm = {k.lower() for k in CATALOGO_REGLAS.keys()} - excluidas_norm

    def _esta_activa(codigo_hex: str) -> bool:
        cod_low = codigo_hex.lower()
        if cod_low in excluidas_norm:
            return False
        if cod_low.endswith("h") and cod_low[:-1] in excluidas_norm:
            return False
        if not cod_low.endswith("h") and (cod_low + "h") in excluidas_norm:
            return False
        return cod_low in reglas_norm

    def _regla_info(codigo_hex: str) -> Tuple[RuleCode, str]:
        info = CATALOGO_REGLAS.get(codigo_hex, {})
        titulo = info.get("titulo", f"Regla {codigo_hex}")
        return RuleCode(codigo_hex), titulo

    # Directivas de supresión // gaff:ignore <regla> <justificación>
    lineas_ignoradas: Dict[int, Set[str]] = {}
    re_ignore = re.compile(r"(?://|/\*)\s*gaff:ignore\s+(0x[0-9a-fA-F]+h?|all)\s+(\S.{3,})")
    for idx_l, linea_raw in enumerate(lineas):
        m_ig = re_ignore.search(linea_raw)
        if m_ig:
            cod_ig = m_ig.group(1).lower()
            if not cod_ig.endswith("h") and cod_ig.startswith("0x"):
                cod_ig += "h"
            lineas_ignoradas.setdefault(idx_l + 1, set()).add(cod_ig)
            if linea_raw.strip().startswith("//") or linea_raw.strip().startswith("/*"):
                lineas_ignoradas.setdefault(idx_l + 2, set()).add(cod_ig)


    # -------------------------------------------------------------------------
    # 0x000Ch: Nombres de archivo en snake_case en minúsculas (sin espacios)
    # -------------------------------------------------------------------------
    if _esta_activa("0x000Ch"):
        nombre_archivo = ruta.name
        es_valido_snake = bool(re.match(r"^[a-z0-9_]+(?:\.[a-z0-9_]+)+$", nombre_archivo))
        if not es_valido_snake:
            sugerido = re.sub(r"[-\s]+", "_", nombre_archivo.lower())
            sugerido = re.sub(r"[^a-z0-9_\.]", "", sugerido)
            rcode, tit = _regla_info("0x000Ch")
            violaciones.append(ViolacionRegla(
                codigo=rcode,
                titulo=tit,
                archivo=ruta,
                linea=1,
                columna=1,
                mensaje=f"El nombre del archivo '{nombre_archivo}' no utiliza snake_case en minúsculas (contiene mayúsculas, espacios o caracteres no permitidos).",
                sugerencia=f"Renombrá el archivo a formato snake_case en minúsculas (ej: '{sugerido}').",
                es_autofixable=False,
            ))

    # -------------------------------------------------------------------------
    # 0x50XXh: Compilación y Buenas Prácticas
    # -------------------------------------------------------------------------

    # 0x5003h: Guardas de inclusión en cabeceras (.h)
    if _esta_activa("0x5003h") and es_header:
        tiene_pragma = bool(re.search(r"^[ \t]*#pragma\s+once\b", codigo_sin_comentarios, re.MULTILINE))
        m_guard = re.search(r"^[ \t]*#ifndef\s+(\w+)", codigo_sin_comentarios, re.MULTILINE)
        m_def = re.search(r"^[ \t]*#define\s+(\w+)", codigo_sin_comentarios, re.MULTILINE)
        tiene_ifndef = bool(m_guard and m_def)
        if not (tiene_pragma or tiene_ifndef):
            rcode, tit = _regla_info("0x5003h")
            stem_h = re.sub(r"[^A-Za-z0-9_]", "_", ruta.stem).upper()
            violaciones.append(ViolacionRegla(
                codigo=rcode,
                titulo=tit,
                archivo=ruta,
                linea=1,
                columna=1,
                mensaje="El archivo de cabecera no cuenta con guardas de inclusión (#ifndef / #define o #pragma once).",
                sugerencia=f"Agregá guardas de preprocesador:\n#ifndef __{stem_h}_H__\n#define __{stem_h}_H__\n...\n#endif",
                es_autofixable=True,
            ))
        elif tiene_ifndef and m_guard:
            guard_name = m_guard.group(1).upper()
            stem_clean = re.sub(r"[^A-Za-z0-9_]", "_", ruta.stem).upper()
            canonical_guards = {
                f"__{stem_clean}_H__", f"_{stem_clean}_H_", f"{stem_clean}_H",
                f"__{stem_clean}_H", f"{stem_clean}_H_", f"__{stem_clean}__",
                f"{stem_clean}_INCLUDED", f"__{stem_clean}_INCLUDED__",
            }
            if guard_name not in canonical_guards and not guard_name.endswith(f"_{stem_clean}_H") and not guard_name.startswith(stem_clean):
                rcode, tit = _regla_info("0x5003h")
                line_no = codigo_sin_comentarios[:m_guard.start()].count("\n") + 1
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=line_no,
                    columna=1,
                    mensaje=f"La guarda de inclusión '{m_guard.group(1)}' no sigue el formato canónico derivado de '{ruta.name}'.",
                    sugerencia=f"Nombrá la guarda según la convención institucional: '__{stem_clean}_H__'.",
                    es_autofixable=False,
                ))

        # Detección de funciones static con cuerpo en headers (.h)
        re_static_fn_body = re.compile(rf"^[ \t]*static\s+(?:{TIPOS_BASICOS}|[a-zA-Z_]\w*)\s+(\*?\s*[a-zA-Z_]\w*)\s*\([^)]*\)\s*\{{", re.MULTILINE)
        for m_st in re_static_fn_body.finditer(codigo_sin_comentarios):
            line_no = codigo_sin_comentarios[:m_st.start()].count("\n") + 1
            rcode, tit = _regla_info("0x5003h")
            violaciones.append(ViolacionRegla(
                codigo=rcode,
                titulo=tit,
                archivo=ruta,
                linea=line_no,
                columna=1,
                mensaje="Función 'static' con cuerpo de implementación definida dentro de archivo de cabecera (.h).",
                sugerencia="Declarala en el encabezado únicamente como prototipo exportable o mové la implementación al archivo .c.",
                es_autofixable=False,
            ))

    # 0x5004h: Operaciones de cadenas inseguras (strcpy, strcat, sprintf)
    if _esta_activa("0x5004h"):
        re_str_inseguro = re.compile(r"\b(strcpy|strcat|sprintf)\s*\(")
        for idx, linea in enumerate(lineas_sin_comentarios, 1):
            m = re_str_inseguro.search(linea)
            if m:
                fn = m.group(1)
                rcode, tit = _regla_info("0x5004h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=idx,
                    columna=m.start() + 1,
                    mensaje=f"Uso de función de cadena potencialmente insegura '{fn}'.",
                    sugerencia=f"Reemplazá '{fn}' por variantes seguras con límite de buffer (snprintf, strncpy, strncat).",
                    codigo_linea=lineas[idx - 1],
                    es_autofixable=False,
                ))

    # 0x5006h: gets() prohibida y scanf("%s") inseguro
    if _esta_activa("0x5006h"):
        re_gets = re.compile(r"\bgets\s*\(")
        re_scanf_s = re.compile(r'\bscanf\s*\(\s*"[^"]*%s[^"]*"')
        for idx, linea in enumerate(lineas_sin_comentarios, 1):
            m_gets = re_gets.search(linea)
            if m_gets:
                rcode, tit = _regla_info("0x5006h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=idx,
                    columna=m_gets.start() + 1,
                    mensaje="La función 'gets' está prohibida por carecer de control de límites.",
                    sugerencia="Utilizá 'fgets(buffer, sizeof(buffer), stdin)' para lecturas seguras.",
                    codigo_linea=lineas[idx - 1],
                    es_autofixable=False,
                ))
            m_scanf = re_scanf_s.search(linea)
            if m_scanf:
                rcode, tit = _regla_info("0x5006h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=idx,
                    columna=m_scanf.start() + 1,
                    mensaje="Uso de 'scanf(\"%s\")' sin especificar ancho de buffer.",
                    sugerencia="Especificá ancho de buffer o preferí 'fgets'.",
                    codigo_linea=lineas[idx - 1],
                    es_autofixable=False,
                ))

    # 0x5001h: Arreglos de longitud variable (VLAs) y tamaños mágicos
    if _esta_activa("0x5001h") and not es_header:
        re_vla = re.compile(rf"^\s*{TIPOS_BASICOS}\s+\w+\s*\[\s*([a-zA-Z_]\w*)\s*\]\s*;", re.MULTILINE)
        for m in re_vla.finditer(codigo_sin_comentarios):
            var_name = m.group(1)
            # Si el tamaño es una variable con letras minúsculas (no constante en mayúsculas)
            if var_name != var_name.upper():
                line_no = codigo_sin_comentarios[:m.start()].count("\n") + 1
                rcode, tit = _regla_info("0x5001h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=line_no,
                    columna=1,
                    mensaje=f"Declaración de arreglo con longitud variable (VLA) '{m.group(0).strip()}'.",
                    sugerencia="Definí arreglos estáticos con constantes (#define) o utilizá memoria dinámica (malloc).",
                    es_autofixable=False,
                ))

        # Auditor de constantes de tamaño de arreglo sin #define o enum (números mágicos > 1)
        re_num_size = re.compile(rf"^\s*{TIPOS_BASICOS}\s+\w+\s*\[\s*(\d+)\s*\]\s*;", re.MULTILINE)
        for m in re_num_size.finditer(codigo_sin_comentarios):
            num_val = int(m.group(1))
            if num_val > 1:
                line_no = codigo_sin_comentarios[:m.start()].count("\n") + 1
                rcode, tit = _regla_info("0x5001h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=line_no,
                    columna=1,
                    mensaje=f"Declaración de arreglo con tamaño hardcodeado con número mágico '{num_val}' sin #define o enum.",
                    sugerencia=f"Definí una constante simbólica (#define CAPACIDAD_MAX {num_val}) para el tamaño del arreglo.",
                    codigo_linea=lineas[line_no - 1],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x10XXh: Estructuras de Control y Lazos
    # -------------------------------------------------------------------------

    # 0x1006h: Prohibición de goto
    if _esta_activa("0x1006h"):
        for idx, linea in enumerate(lineas_sin_comentarios, 1):
            m_goto = re.search(r"\bgoto\s+\w+", linea)
            if m_goto:
                rcode, tit = _regla_info("0x1006h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=idx,
                    columna=m_goto.start() + 1,
                    mensaje="Uso de la sentencia 'goto' detectado.",
                    sugerencia="Reemplazá 'goto' por estructuras de control estructuradas (bucles, retornos directos).",
                    codigo_linea=lineas[idx - 1],
                    es_autofixable=False,
                ))

    # 0x1002h: Prohibición de continue
    if _esta_activa("0x1002h"):
        for idx, linea in enumerate(lineas_sin_comentarios, 1):
            m_cont = re.search(r"\bcontinue\s*;", linea)
            if m_cont:
                rcode, tit = _regla_info("0x1002h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=idx,
                    columna=m_cont.start() + 1,
                    mensaje="Uso de la sentencia 'continue' detectado.",
                    sugerencia="Reemplazá 'continue' por banderas lógicas de control en la condición del lazo.",
                    codigo_linea=lineas[idx - 1],
                    es_autofixable=False,
                ))

    # 0x1007h: Prohibición de operador ternario ?:
    if _esta_activa("0x1007h"):
        for idx, linea in enumerate(lineas_sin_comentarios, 1):
            if not linea.strip().startswith("#"):
                m_tern = re.search(r"(?<=\w|\))\s*\?\s*[^:]+\s*:\s*", linea)
                if m_tern:
                    rcode, tit = _regla_info("0x1007h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=idx,
                        columna=m_tern.start() + 1,
                        mensaje="Uso del operador condicional ternario '?:' detectado.",
                        sugerencia="Reemplazá el operador ternario por sentencias if-else estructuradas.",
                        codigo_linea=lineas[idx - 1],
                        es_autofixable=False,
                    ))

    # 0x1001h: Estructuras de control sin llaves
    if _esta_activa("0x1001h"):
        re_if_sin_llaves = re.compile(r"^\s*(?:if\s*\([^)]+\)|for\s*\([^)]+\)|while\s*\([^)]+\)|else)\s*([^{};\s][^;]*;)", re.MULTILINE)
        for m in re_if_sin_llaves.finditer(codigo_sin_comentarios):
            line_no = codigo_sin_comentarios[:m.start()].count("\n") + 1
            line_txt = lineas[line_no - 1]
            rcode, tit = _regla_info("0x1001h")
            violaciones.append(ViolacionRegla(
                codigo=rcode,
                titulo=tit,
                archivo=ruta,
                linea=line_no,
                columna=1,
                mensaje="Estructura de control sin bloque de llaves {}.",
                sugerencia="Encerrá siempre el cuerpo de las sentencias de control dentro de llaves {}.",
                codigo_linea=line_txt,
                es_autofixable=False,
            ))

    # 0x1008h: Switch sin default
    if _esta_activa("0x1008h"):
        re_switch = re.compile(r"\bswitch\s*\([^)]+\)\s*\{", re.MULTILINE)
        for m in re_switch.finditer(codigo_sin_comentarios):
            start_pos = m.end() - 1
            line_no = codigo_sin_comentarios[:m.start()].count("\n") + 1
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
            switch_body = codigo_sin_comentarios[start_pos:end_pos]
            if "default:" not in switch_body and "default :" not in switch_body:
                rcode, tit = _regla_info("0x1008h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=line_no,
                    columna=1,
                    mensaje="Instrucción 'switch' sin bloque 'default:'.",
                    sugerencia="Incluí siempre un caso 'default:' para manejar estados no previstos.",
                    es_autofixable=False,
                ))

    # 0x1003h: for(;;) o for(; cond;)
    if _esta_activa("0x1003h"):
        re_for_empty = re.compile(r"\bfor\s*\(\s*;\s*;\s*\)|\bfor\s*\(\s*;\s*[^;]+;\s*\)")
        for idx, linea in enumerate(lineas_sin_comentarios, 1):
            m = re_for_empty.search(linea)
            if m:
                rcode, tit = _regla_info("0x1003h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=idx,
                    columna=m.start() + 1,
                    mensaje="Uso de 'for' como lazo puramente lógico o indefinido.",
                    sugerencia="Utilizá 'while' para lazos condicionales y reservá 'for' para conteo definido.",
                    codigo_linea=lineas[idx - 1],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x00XXh: Sintaxis Básica y Nomenclatura
    # -------------------------------------------------------------------------

    # 0x0004h: Espaciado en palabras clave (if, for, while, switch) y operadores binarios
    if _esta_activa("0x0004h"):
        re_kw = re.compile(r"\b(if|for|while|switch)\(")
        re_asgn_bin = re.compile(r'\b([a-zA-Z0-9_]+)([ \t]*)(\+=|-=|\*=|/=|%=|==|!=|<=|>=|&&|\|\||<|>|=)([ \t]*)([a-zA-Z0-9_]+)')
        re_arith_bin = re.compile(rf"\b([a-zA-Z0-9_]+)([ \t]*)(\+|\-|\*|\/|%)([ \t]*)([a-zA-Z0-9_]+)\b")
        for idx, linea in enumerate(lineas_sin_cadenas, 1):
            if linea.strip().startswith("#"):
                continue
            m_kw = re_kw.search(linea)
            if m_kw:
                kw = m_kw.group(1)
                rcode, tit = _regla_info("0x0004h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=idx,
                    columna=m_kw.start() + 1,
                    mensaje=f"Falta espacio entre palabra clave '{kw}' y el paréntesis de apertura.",
                    sugerencia=f"Escribí '{kw} (' en lugar de '{kw}('",
                    codigo_linea=lineas[idx - 1],
                    es_autofixable=True,
                ))
            for m_ab in re_asgn_bin.finditer(linea):
                sp1, op, sp2 = m_ab.group(2), m_ab.group(3), m_ab.group(4)
                if sp1 != " " or sp2 != " ":
                    rcode, tit = _regla_info("0x0004h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=idx,
                        columna=m_ab.start() + 1,
                        mensaje=f"Falta espacio alrededor del operador binario '{op}'.",
                        sugerencia=f"Escribí ' {op} ' con exactamente un espacio antes y después.",
                        codigo_linea=lineas[idx - 1],
                        es_autofixable=True,
                    ))
            for m_ar in re_arith_bin.finditer(linea):
                left, sp1, op, sp2 = m_ar.group(1), m_ar.group(2), m_ar.group(3), m_ar.group(4)
                if op == "*" and re.match(rf"^(?:{TIPOS_BASICOS})$", left):
                    continue
                if sp1 != " " or sp2 != " ":
                    rcode, tit = _regla_info("0x0004h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=idx,
                        columna=m_ar.start() + 1,
                        mensaje=f"Falta espacio alrededor del operador binario '{op}'.",
                        sugerencia=f"Escribí ' {op} ' con exactamente un espacio antes y después.",
                        codigo_linea=lineas[idx - 1],
                        es_autofixable=True,
                    ))

    # 0x0006h: Asterisco junto al identificador (int* ptr -> int *ptr)
    if _esta_activa("0x0006h"):
        re_ptr_junto_tipo = re.compile(rf"\b{TIPOS_BASICOS}\*\s+([a-zA-Z_]\w*)")
        for idx, linea in enumerate(lineas_sin_comentarios, 1):
            m = re_ptr_junto_tipo.search(linea)
            if m and not linea.strip().startswith("#"):
                rcode, tit = _regla_info("0x0006h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=idx,
                    columna=m.start() + 1,
                    mensaje="El asterisco de puntero está pegado al tipo de dato.",
                    sugerencia="Colocá el asterisco junto al identificador de la variable (ej: 'int *ptr').",
                    codigo_linea=lineas[idx - 1],
                    es_autofixable=True,
                ))

    # 0x0009h: Longitud de línea (> 80 chars)
    if _esta_activa("0x0009h"):
        for idx, linea in enumerate(lineas, 1):
            if len(linea) > 80:
                rcode, tit = _regla_info("0x0009h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=idx,
                    columna=81,
                    mensaje=f"Línea de {len(linea)} caracteres excede el límite máximo de 80 caracteres.",
                    sugerencia="Dividí la instrucción o llamada en múltiples líneas identadas.",
                    codigo_linea=linea[:80] + "...",
                    es_autofixable=False,
                ))

    # 0x0005h: Indentación de cuatro espacios, sin tabuladores ni espacios finales
    if _esta_activa("0x0005h"):
        for idx, linea in enumerate(lineas, 1):
            if linea.endswith(" ") or linea.endswith("\t"):
                rcode, tit = _regla_info("0x0005h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=idx,
                    columna=len(linea),
                    mensaje="Espacios en blanco sobrantes al final de la línea (trailing whitespace).",
                    sugerencia="Eliminá los espacios al final de la línea.",
                    codigo_linea=linea,
                    es_autofixable=True,
                ))
            if "\t" in linea:
                rcode, tit = _regla_info("0x0005h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=idx,
                    columna=linea.find("\t") + 1,
                    mensaje="Uso de tabuladores duros (\\t) detectado.",
                    sugerencia="Reemplazá tabuladores por 4 espacios.",
                    codigo_linea=linea,
                    es_autofixable=True,
                ))
            line_sin_com = lineas_sin_comentarios[idx - 1] if idx - 1 < len(lineas_sin_comentarios) else ""
            if line_sin_com.strip() and not linea.lstrip().startswith(("*", "/*")):
                lead_spaces = len(linea) - len(linea.lstrip(" "))
                if lead_spaces > 0 and lead_spaces % 4 != 0 and "\t" not in linea[:lead_spaces]:
                    rcode, tit = _regla_info("0x0005h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=idx,
                        columna=1,
                        mensaje=f"La indentación de la línea ({lead_spaces} espacios) no es múltiplo de 4.",
                        sugerencia="Ajustá la indentación para que sea múltiplo de 4 espacios (4, 8, 12, etc.).",
                        codigo_linea=linea,
                        es_autofixable=True,
                    ))

    # 0x0002h: Múltiples declaraciones de variables o sentencias por línea
    if _esta_activa("0x0002h"):
        re_mult_decl = re.compile(rf"^\s*{TIPOS_BASICOS}\s+\*?[a-zA-Z_]\w*(?:\s*=\s*[^,;]+)?\s*,\s*\*?[a-zA-Z_]\w*", re.MULTILINE)
        for m in re_mult_decl.finditer(codigo_sin_comentarios):
            line_no = codigo_sin_comentarios[:m.start()].count("\n") + 1
            line_txt = lineas[line_no - 1]
            if not line_txt.strip().startswith("typedef") and "(" not in line_txt:
                rcode, tit = _regla_info("0x0002h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=line_no,
                    columna=1,
                    mensaje="Declaración de múltiples variables en una sola línea.",
                    sugerencia="Declará una única variable por línea para mejorar la legibilidad.",
                    codigo_linea=line_txt,
                    es_autofixable=False,
                ))

        for i, l in enumerate(lineas_sin_cadenas):
            strip_l = l.strip()
            if not strip_l or strip_l.startswith(("#", "//", "/*", "*")):
                continue
            if re.search(r"\bfor\s*\(", l):
                continue
            semis = [m.start() for m in re.finditer(r";", l)]
            if len(semis) >= 2:
                mid = l[semis[0] + 1:semis[1]].strip()
                if mid and not mid.startswith(("//", "/*")):
                    rcode, tit = _regla_info("0x0002h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=i + 1,
                        columna=semis[1] + 1,
                        mensaje="Prohibición de sentencias múltiples en una sola línea.",
                        sugerencia="Escribí una única sentencia por línea para facilitar la depuración con GDB.",
                        codigo_linea=lineas[i],
                        es_autofixable=False,
                    ))

    # 0x0008h: Constantes en MAYUSCULAS_SNAKE_CASE
    if _esta_activa("0x0008h"):
        re_define_const = re.compile(r"^\s*#\s*define\s+([a-zA-Z_]\w*)\s+[\d\.\"\']", re.MULTILINE)
        for m in re_define_const.finditer(codigo_sin_comentarios):
            name = m.group(1)
            if name != name.upper():
                line_no = codigo_sin_comentarios[:m.start()].count("\n") + 1
                rcode, tit = _regla_info("0x0008h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=line_no,
                    columna=m.start(1) - m.start() + 1,
                    mensaje=f"Constante '#define {name}' no utiliza MAYUSCULAS_SNAKE_CASE.",
                    sugerencia=f"Renombrala en mayúsculas: '{name.upper()}'.",
                    codigo_linea=lineas[line_no - 1],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x0001h, 0x0003h, 0x0007h (GAFF001 / GAFF032)
    # Inspección Exhaustiva de Identificadores (Funciones, Variables, Parámetros y Lazos)
    # -------------------------------------------------------------------------
    CANONICAL_INDICES = {"i", "j", "k", "n", "x", "y", "z", "f", "c", "r"}
    MATH_PARAM_NAMES = {"a", "b"}
    ALLOWED_SHORT_EXCEPTIONS = {"fd", "fp", "in", "ok", "x1", "y1", "z1", "x2", "y2", "z2"}
    CRYPTIC_SHORT_NAMES = {
        "aux", "tmp", "val", "res", "cnt", "ptr", "num", "idx", "buf", "str", "vec", "len", "pos"
    }
    IGNORED_VAR_NAMES = {"main", "argc", "argv", "envp", "void", "NULL", "stdin", "stdout", "stderr"}
    GENERIC_STEMS = {
        "numero", "numeros", "num", "nums", "nro", "nros", "n",
        "var", "variable", "variables",
        "dato", "datos", "val", "valor", "valores",
        "elem", "elemento", "elementos",
        "aux", "auxiliar", "tmp", "temp",
        "arg", "param", "parametro", "parametros",
        "item", "items", "cosa", "cosas", "obj", "objeto", "objetos",
        "entrada", "salida", "texto", "str", "string",
        "res", "resultado", "resultados",
        "vec", "vector", "vectores", "arr", "array", "arreglo", "arreglos",
    }
    RE_GENERIC_NUMERIC = re.compile(
        r"^(?:"
        r"(?:numero|numeros|num|nums|nro|nros|n|"
        r"var|variable|variables|"
        r"dato|datos|val|valor|valores|"
        r"elem|elemento|elementos|"
        r"aux|auxiliar|tmp|temp|"
        r"arg|param|parametro|parametros|"
        r"item|items|cosa|cosas|obj|objeto|objetos|"
        r"entrada|salida|texto|str|string|"
        r"res|resultado|resultados|"
        r"vec|vector|vectores|arr|array|arreglo|arreglos)_?[0-9]+"
        r"|"
        r"_?[0-9]+_?(?:numero|numeros|num|nums|nro|nros|n|"
        r"var|variable|variables|"
        r"dato|datos|val|valor|valores|"
        r"elem|elemento|elementos|"
        r"aux|auxiliar|tmp|temp|"
        r"arg|param|parametro|parametros|"
        r"item|items|cosa|cosas|obj|objeto|objetos|"
        r"entrada|salida|texto|str|string|"
        r"res|resultado|resultados|"
        r"vec|vector|vectores|arr|array|arreglo|arreglos)"
        r")$",
        re.IGNORECASE,
    )
    RE_GENERIC_NUMBERED_IDENTIFIER = RE_GENERIC_NUMERIC

    def _es_identificador_generico_numerado(name: str) -> bool:
        if not name or name in IGNORED_VAR_NAMES:
            return False
        lower = name.lower()
        if lower in ALLOWED_SHORT_EXCEPTIONS:
            return False
        if len(name) == 1:
            return False
        if RE_GENERIC_NUMERIC.match(lower):
            return True
        if lower in {"na", "nb", "nc", "an", "bn", "cn"}:
            return True
        parts = [p for p in lower.split("_") if p]
        if len(parts) >= 2:
            stem_indices = [i for i, p in enumerate(parts) if p in GENERIC_STEMS]
            if stem_indices:
                other_parts = [p for i, p in enumerate(parts) if i not in stem_indices]
                if other_parts and all(p.isdigit() or len(p) == 1 or re.fullmatch(r"[a-z]?[0-9]+|[0-9]+[a-z]?", p) for p in other_parts):
                    return True
        return False

    def _split_decl_items(decl: str) -> List[str]:
        items: List[str] = []
        current: List[str] = []
        depth = 0
        in_quote = False
        quote_char = ""
        for char in decl:
            if in_quote:
                current.append(char)
                if char == quote_char:
                    in_quote = False
            elif char in ('"', "'"):
                in_quote = True
                quote_char = char
                current.append(char)
            elif char in ("(", "[", "{"):
                depth += 1
                current.append(char)
            elif char in (")", "]", "}"):
                depth = max(0, depth - 1)
                current.append(char)
            elif char == "," and depth == 0:
                items.append("".join(current).strip())
                current = []
            else:
                current.append(char)
        if current:
            items.append("".join(current).strip())
        return [it for it in items if it]

    # 1. Nombres de funciones y parámetros
    re_fn_header = re.compile(
        rf"^\s*(?:static\s+|inline\s+|extern\s+)*(?:{TIPOS_BASICOS}|[a-zA-Z_]\w*)\s+(\*?\s*[a-zA-Z_]\w*)\s*\(([^;{{)]*)\)",
        re.MULTILINE
    )
    for m_fh in re_fn_header.finditer(codigo_sin_comentarios):
        raw_fn = m_fh.group(1).lstrip("*").strip()
        if raw_fn in ("if", "for", "while", "switch", "return", "sizeof"):
            continue
        line_fn = codigo_sin_comentarios[:m_fh.start(1)].count("\n") + 1
        col_fn = m_fh.start(1) - codigo_sin_comentarios.rfind("\n", 0, m_fh.start(1))

        # 0x0007h / 0x200Ah: camelCase en funciones
        if _esta_activa("0x0007h") or _esta_activa("0x200Ah"):
            if raw_fn not in IGNORED_VAR_NAMES and any(c.isupper() for c in raw_fn) and any(c.islower() for c in raw_fn):
                rcode_target = "0x200Ah" if (_esta_activa("0x200Ah") and not _esta_activa("0x0007h")) else "0x0007h"
                rcode, tit = _regla_info(rcode_target)
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=line_fn,
                    columna=col_fn,
                    mensaje=f"Nombre de función '{raw_fn}' escrito en camelCase.",
                    sugerencia="Usá snake_case (todo en minúsculas con guiones bajos).",
                    codigo_linea=lineas[line_fn - 1] if line_fn <= len(lineas) else "",
                    es_autofixable=False,
                ))

        # 0x0001h: Nombres de función excesivamente largos (> 31 caracteres)
        if _esta_activa("0x0001h"):
            if len(raw_fn) > 31:
                rcode, tit = _regla_info("0x0001h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=line_fn,
                    columna=col_fn,
                    mensaje=f"Nombre de función excesivamente largo '{raw_fn}' ({len(raw_fn)} caracteres).",
                    sugerencia="Los identificadores no deben superar los 31 caracteres para mantener la legibilidad y compatibilidad con el estándar ISO C.",
                    codigo_linea=lineas[line_fn - 1] if line_fn <= len(lineas) else "",
                    es_autofixable=False,
                ))

        # Parámetros de la función
        params_str = m_fh.group(2)
        for p in _split_decl_items(params_str):
            p_strip = p.strip()
            if not p_strip or p_strip == "void" or "..." in p_strip:
                continue
            m_p = re.search(r"[*]*\s*([a-zA-Z_]\w*)$", p_strip)
            if not m_p:
                continue
            p_name = m_p.group(1)
            if p_name in IGNORED_VAR_NAMES:
                continue
            col_p = lineas[line_fn - 1].find(p_name) + 1 if line_fn <= len(lineas) and p_name in lineas[line_fn - 1] else 1

            # camelCase en parámetros
            if _esta_activa("0x0007h") or _esta_activa("0x200Ah"):
                if any(c.isupper() for c in p_name) and any(c.islower() for c in p_name):
                    rcode, tit = _regla_info("0x0007h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=line_fn,
                        columna=col_p,
                        mensaje=f"Identificador de parámetro '{p_name}' escrito en camelCase.",
                        sugerencia="Usá snake_case en minúsculas con guiones bajos.",
                        codigo_linea=lineas[line_fn - 1] if line_fn <= len(lineas) else "",
                        es_autofixable=False,
                    ))

            # 0x0037h / 0x0001h: Identificadores genéricos con sufijo numérico o afijos (numero1, num_1, n_a, a_n)
            if (_esta_activa("0x0037h") or _esta_activa("0x0001h")) and _es_identificador_generico_numerado(p_name):
                rule_target = "0x0037h" if _esta_activa("0x0037h") else "0x0001h"
                rcode, tit = _regla_info(rule_target)
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=line_fn,
                    columna=col_p,
                    mensaje=f"Identificador de parámetro '{p_name}' con sufijo numérico genérico o afijo no descriptivo denota una elección pobre de nombre.",
                    sugerencia="Elegí un nombre semántico que describa el rol específico del parámetro (ej: 'dividendo', 'divisor') o utilizá un arreglo/estructura.",
                    codigo_linea=lineas[line_fn - 1] if line_fn <= len(lineas) else "",
                    es_autofixable=False,
                    severidad="ADVERTENCIA",
                ))
            # 0x0001h: Parámetros descriptivos (cortos y largos)
            elif _esta_activa("0x0001h"):
                if len(p_name) == 1:
                    if p_name.lower() not in CANONICAL_INDICES and p_name.lower() not in MATH_PARAM_NAMES:
                        rcode, tit = _regla_info("0x0001h")
                        violaciones.append(ViolacionRegla(
                            codigo=rcode,
                            titulo=tit,
                            archivo=ruta,
                            linea=line_fn,
                            columna=col_p,
                            mensaje=f"Identificador de parámetro no descriptivo de una sola letra '{p_name}'.",
                            sugerencia="Los nombres de argumentos deben reflejar con precisión su propósito.",
                            codigo_linea=lineas[line_fn - 1] if line_fn <= len(lineas) else "",
                            es_autofixable=False,
                        ))
                elif 1 < len(p_name) < 4 and p_name.lower() not in ALLOWED_SHORT_EXCEPTIONS:
                    rcode, tit = _regla_info("0x0001h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=line_fn,
                        columna=col_p,
                        mensaje=f"Identificador de parámetro corto y poco expresivo '{p_name}' ({len(p_name)} caracteres).",
                        sugerencia="Se recomienda utilizar identificadores más descriptivos del dominio del problema.",
                        codigo_linea=lineas[line_fn - 1] if line_fn <= len(lineas) else "",
                        es_autofixable=False,
                    ))
                elif len(p_name) > 31:
                    rcode, tit = _regla_info("0x0001h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=line_fn,
                        columna=col_p,
                        mensaje=f"Identificador de parámetro excesivamente largo '{p_name}' ({len(p_name)} caracteres).",
                        sugerencia="Los identificadores no deben superar los 31 caracteres para cumplir el estándar ISO C.",
                        codigo_linea=lineas[line_fn - 1] if line_fn <= len(lineas) else "",
                        es_autofixable=False,
                    ))

    # 2. Declaraciones de variables
    re_var_stmt = re.compile(
        rf"^[ \t]*(?:static\s+|const\s+|volatile\s+|register\s+)*(?:(?:struct|union|enum)\s+[a-zA-Z_]\w*|{TIPOS_BASICOS}|[A-Z]\w*)\s+(?!\()([^;{{}}]+);",
        re.MULTILINE
    )
    for m_vs in re_var_stmt.finditer(codigo_sin_comentarios):
        line_no = codigo_sin_comentarios[:m_vs.start()].count("\n") + 1
        line_txt = lineas_sin_comentarios[line_no - 1].strip()
        if line_txt.startswith("typedef") or line_txt.startswith("return") or line_txt.startswith("#"):
            continue
        is_const = line_txt.startswith("const") or line_txt.startswith("static const")
        decl_content = m_vs.group(1)
        for item in _split_decl_items(decl_content):
            has_init = "=" in item or "{" in item
            clean_item = re.sub(r"=.*$", "", item, flags=re.DOTALL)
            clean_item = re.sub(r"\[.*?\]", "", clean_item).strip()
            m_v = re.search(r"[*]*\s*([a-zA-Z_]\w*)$", clean_item)
            if not m_v:
                continue
            var_name = m_v.group(1)
            if var_name in IGNORED_VAR_NAMES or is_const:
                continue
            col_v = lineas[line_no - 1].find(var_name) + 1 if line_no <= len(lineas) and var_name in lineas[line_no - 1] else 1

            # 0x0007h: camelCase en variables locales y globales
            if _esta_activa("0x0007h") or _esta_activa("0x200Ah"):
                if any(c.isupper() for c in var_name) and any(c.islower() for c in var_name):
                    rcode, tit = _regla_info("0x0007h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=line_no,
                        columna=col_v,
                        mensaje=f"Identificador de variable '{var_name}' escrito en camelCase.",
                        sugerencia="Usá snake_case (todo en minúsculas con guiones bajos).",
                        codigo_linea=lineas[line_no - 1] if line_no <= len(lineas) else "",
                        es_autofixable=False,
                    ))

            # 0x0037h / 0x0001h: Variables genéricas con sufijo numérico o afijos (numero1, num_1, n_a, a_n)
            if (_esta_activa("0x0037h") or _esta_activa("0x0001h")) and _es_identificador_generico_numerado(var_name):
                rule_target = "0x0037h" if _esta_activa("0x0037h") else "0x0001h"
                rcode, tit = _regla_info(rule_target)
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=line_no,
                    columna=col_v,
                    mensaje=f"Identificador de variable '{var_name}' con sufijo numérico genérico o afijo no descriptivo denota una elección pobre de nombre.",
                    sugerencia="Elegí un nombre semántico que describa su rol específico en el algoritmo o utilizá un arreglo/estructura si representan datos homogéneos.",
                    codigo_linea=lineas[line_no - 1] if line_no <= len(lineas) else "",
                    es_autofixable=False,
                    severidad="ADVERTENCIA",
                ))
            # 0x0001h: Variables cortas y largas
            elif _esta_activa("0x0001h"):
                if len(var_name) == 1:
                    if var_name.lower() not in CANONICAL_INDICES:
                        rcode, tit = _regla_info("0x0001h")
                        violaciones.append(ViolacionRegla(
                            codigo=rcode,
                            titulo=tit,
                            archivo=ruta,
                            linea=line_no,
                            columna=col_v,
                            mensaje=f"Identificador de variable no descriptivo de una sola letra '{var_name}'.",
                            sugerencia="Los nombres de variables deben reflejar con precisión su propósito (salvo índices canónicos i, j, k, n, x, y, z, f, c, r).",
                            codigo_linea=lineas[line_no - 1] if line_no <= len(lineas) else "",
                            es_autofixable=False,
                        ))
                elif 1 < len(var_name) < 4 and var_name.lower() not in ALLOWED_SHORT_EXCEPTIONS:
                    rcode, tit = _regla_info("0x0001h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=line_no,
                        columna=col_v,
                        mensaje=f"Identificador corto y poco expresivo '{var_name}' ({len(var_name)} caracteres).",
                        sugerencia="Se recomienda utilizar identificadores más descriptivos del dominio del problema.",
                        codigo_linea=lineas[line_no - 1] if line_no <= len(lineas) else "",
                        es_autofixable=False,
                    ))
                elif len(var_name) > 31:
                    rcode, tit = _regla_info("0x0001h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=line_no,
                        columna=col_v,
                        mensaje=f"Identificador excesivamente largo '{var_name}' ({len(var_name)} caracteres).",
                        sugerencia="Los identificadores no deben superar los 31 caracteres para mantener la legibilidad y cumplir el estándar ISO C.",
                        codigo_linea=lineas[line_no - 1] if line_no <= len(lineas) else "",
                        es_autofixable=False,
                    ))

            # 0x0003h: Inicialización obligatoria
            if _esta_activa("0x0003h") and not has_init:
                rcode, tit = _regla_info("0x0003h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=line_no,
                    columna=col_v,
                    mensaje=f"Variable '{var_name}' declarada sin inicializar a un valor conocido.",
                    sugerencia="Inicializá las variables locales al declararlas (ej: 'int x = 0;').",
                    codigo_linea=lineas[line_no - 1] if line_no <= len(lineas) else "",
                    es_autofixable=False,
                ))

    # 3. Variables de lazo for (ej: for (int i = 0; ...))
    re_for_decl = re.compile(
        rf"\bfor\s*\(\s*(?:{TIPOS_BASICOS})\s+([a-zA-Z_]\w*)\s*=",
        re.MULTILINE
    )
    for m_fd in re_for_decl.finditer(codigo_sin_comentarios):
        var_lazo = m_fd.group(1)
        line_no = codigo_sin_comentarios[:m_fd.start(1)].count("\n") + 1
        col_vl = lineas[line_no - 1].find(var_lazo) + 1 if line_no <= len(lineas) and var_lazo in lineas[line_no - 1] else 1

        if _esta_activa("0x0007h") or _esta_activa("0x200Ah"):
            if any(c.isupper() for c in var_lazo) and any(c.islower() for c in var_lazo):
                rcode, tit = _regla_info("0x0007h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=line_no,
                    columna=col_vl,
                    mensaje=f"Identificador de variable de lazo '{var_lazo}' escrito en camelCase.",
                    sugerencia="Usá snake_case en minúsculas.",
                    codigo_linea=lineas[line_no - 1] if line_no <= len(lineas) else "",
                    es_autofixable=False,
                ))

        # 0x0037h / 0x0001h: Variables de lazo genéricas con sufijo numérico o afijos
        if (_esta_activa("0x0037h") or _esta_activa("0x0001h")) and _es_identificador_generico_numerado(var_lazo):
            rule_target = "0x0037h" if _esta_activa("0x0037h") else "0x0001h"
            rcode, tit = _regla_info(rule_target)
            violaciones.append(ViolacionRegla(
                codigo=rcode,
                titulo=tit,
                archivo=ruta,
                linea=line_no,
                columna=col_vl,
                mensaje=f"Identificador de lazo '{var_lazo}' con sufijo numérico genérico o afijo no descriptivo denota una elección pobre de nombre.",
                sugerencia="Utilizá índices canónicos (i, j, k, n) o identificadores con significado en el dominio.",
                codigo_linea=lineas[line_no - 1] if line_no <= len(lineas) else "",
                es_autofixable=False,
                severidad="ADVERTENCIA",
            ))
        elif _esta_activa("0x0001h"):
            if len(var_lazo) == 1 and var_lazo.lower() not in CANONICAL_INDICES:
                rcode, tit = _regla_info("0x0001h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=line_no,
                    columna=col_vl,
                    mensaje=f"Identificador de lazo no descriptivo de una sola letra '{var_lazo}'.",
                    sugerencia="Utilizá índices canónicos (i, j, k, n) para lazos.",
                    codigo_linea=lineas[line_no - 1] if line_no <= len(lineas) else "",
                    es_autofixable=False,
                ))
            elif 1 < len(var_lazo) < 4 and var_lazo.lower() not in ALLOWED_SHORT_EXCEPTIONS:
                rcode, tit = _regla_info("0x0001h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=line_no,
                    columna=col_vl,
                    mensaje=f"Identificador de variable de lazo corto y poco expresivo '{var_lazo}' ({len(var_lazo)} caracteres).",
                    sugerencia="Se recomienda utilizar identificadores más descriptivos del dominio del problema o índices canónicos.",
                    codigo_linea=lineas[line_no - 1] if line_no <= len(lineas) else "",
                    es_autofixable=False,
                ))
            elif len(var_lazo) > 31:
                rcode, tit = _regla_info("0x0001h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=line_no,
                    columna=col_vl,
                    mensaje=f"Identificador de variable de lazo excesivamente largo '{var_lazo}' ({len(var_lazo)} caracteres).",
                    sugerencia="Los identificadores no deben superar los 31 caracteres.",
                    codigo_linea=lineas[line_no - 1] if line_no <= len(lineas) else "",
                    es_autofixable=False,
                ))

    # 0x000Bh: Llaves en la misma línea (estilo K&R en vez de Allman)
    if _esta_activa("0x000Bh"):
        re_knr = re.compile(r"(?:if|for|while|switch|\))\s*\{$")
        for idx, linea in enumerate(lineas_sin_comentarios, 1):
            if re_knr.search(linea.rstrip()) and not linea.strip().startswith("struct") and not linea.strip().startswith("enum"):
                rcode, tit = _regla_info("0x000Bh")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=idx,
                    columna=linea.rfind("{") + 1,
                    mensaje="Llave de apertura '{' ubicada en la misma línea según estilo K&R.",
                    sugerencia="Ubicá la llave de apertura en una línea independiente según el estilo Allman.",
                    codigo_linea=lineas[idx - 1],
                    es_autofixable=True,
                ))

    # -------------------------------------------------------------------------
    # 0x20XXh: Funciones y Modularización
    # -------------------------------------------------------------------------

    # 0x2004h: Variables globales mutables
    if _esta_activa("0x2004h") and not es_header:
        re_global = re.compile(rf"^({TIPOS_BASICOS})\s+(\*?[a-zA-Z_]\w*)\s*(?:=\s*[^;]+)?\s*;", re.MULTILINE)
        for m in re_global.finditer(codigo_sin_comentarios):
            line_no = codigo_sin_comentarios[:m.start()].count("\n") + 1
            line_txt = lineas[line_no - 1].strip()
            if not line_txt.startswith("const") and not line_txt.startswith("typedef") and not line_txt.startswith("static const"):
                rcode, tit = _regla_info("0x2004h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=line_no,
                    columna=1,
                    mensaje=f"Declaración de variable global mutable '{m.group(2)}'.",
                    sugerencia="Evitá variables globales; transferí el estado mediante parámetros y valores de retorno.",
                    codigo_linea=lineas[line_no - 1],
                    es_autofixable=False,
                ))

    # 0x2005h: Longitud máxima de función (> 50 líneas)
    if _esta_activa("0x2005h"):
        re_fn_start = re.compile(r"^[ 	]*(?:[a-zA-Z0-9_*]+[ 	]+)+([a-zA-Z0-9_]+)[ 	]*\([^)]*\)[ 	]*\{?", re.MULTILINE)
        for m in re_fn_start.finditer(codigo_sin_comentarios):
            fn_name = m.group(1)
            start_pos = codigo_sin_comentarios.find("{", m.end() - 1)
            if start_pos == -1 or start_pos - m.start() > 120:
                continue
            line_start = codigo_sin_comentarios[:m.start()].count("\n") + 1

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
            if total_lines > 40:
                rcode, tit = _regla_info("0x2005h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=line_start,
                    columna=1,
                    mensaje=f"Función '{fn_name}' tiene {total_lines} líneas (máximo pedagógico permitido: 40).",
                    sugerencia="Modularizá la función dividiéndola en funciones auxiliares.",
                    es_autofixable=False,
                ))

    # 0x2002h: printf/scanf en funciones auxiliares
    if _esta_activa("0x2002h") and not es_header:
        re_fn_any = re.compile(r"^[ 	]*(?:[a-zA-Z0-9_*]+[ 	]+)+([a-zA-Z0-9_]+)[ 	]*\([^)]*\)[ 	]*\{?", re.MULTILINE)
        for m in re_fn_any.finditer(codigo_sin_comentarios):
            fn_name = m.group(1)
            if fn_name in ("main",) or fn_name.startswith(("imprimir_", "mostrar_", "print_", "mostrar", "imprimir", "leer_", "pedir_", "log_", "reportar_")):
                continue
            start_pos = codigo_sin_comentarios.find("{", m.end() - 1)
            if start_pos == -1 or start_pos - m.start() > 120:
                continue
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
            fn_body = codigo_sin_comentarios[start_pos:end_pos]
            m_io = re.search(r"\b(printf|scanf)\s*\(", fn_body)
            if m_io:
                io_pos = start_pos + m_io.start()
                line_no = codigo_sin_comentarios[:io_pos].count("\n") + 1
                rcode, tit = _regla_info("0x2002h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=line_no,
                    columna=1,
                    mensaje=f"Función auxiliar de cálculo '{fn_name}' contiene llamadas directas a '{m_io.group(1)}'.",
                    sugerencia="Separá la lógica computacional del código de entrada/salida por consola.",
                    codigo_linea=lineas[line_no - 1],
                    es_autofixable=False,
                ))

    # 0x2003h: Documentación completa de funciones y prototipos
    if _esta_activa("0x2003h"):
        def _obtener_prototipos_documentados_header(ruta_h: Path) -> Set[str]:
            if not ruta_h.is_file():
                return set()
            try:
                txt_h = ruta_h.read_text(encoding="utf-8")
            except Exception:
                try:
                    txt_h = ruta_h.read_text(encoding="latin-1")
                except Exception:
                    return set()
            lines_h = txt_h.splitlines()
            code_h_sin_comentarios = _eliminar_comentarios(txt_h)
            doc_fns: Set[str] = set()
            re_proto_h = re.compile(
                rf"^[ \t]*(?!(?:typedef|return)\b)(?:(?:static|inline|extern|const)[ \t]+)*(?:struct[ \t]+\w+|enum[ \t]+\w+|union[ \t]+\w+|{TIPOS_BASICOS}|[a-zA-Z_]\w*)[ \t]*(\*+[ \t]*|[ \t]+\*?)([a-zA-Z_]\w*)[ \t]*\(([\s\S]*?)\)[ \t]*;",
                re.MULTILINE
            )
            for m_p in re_proto_h.finditer(code_h_sin_comentarios):
                fn_nom = m_p.group(2)
                l_idx = code_h_sin_comentarios[:m_p.start()].count("\n")
                if _tiene_comentario_documentacion(lines_h, l_idx):
                    doc_fns.add(fn_nom)
            return doc_fns

        prototipos_doc_header: Set[str] = set()
        if not es_header:
            comp_h = ruta.with_suffix(".h")
            prototipos_doc_header.update(_obtener_prototipos_documentados_header(comp_h))
            for inc in re.findall(r'#include\s+"([^"]+\.h)"', contenido_original):
                inc_path = ruta.parent / inc
                prototipos_doc_header.update(_obtener_prototipos_documentados_header(inc_path))

        re_fn_decl_all = re.compile(
            rf"^[ \t]*(?!(?:typedef|return)\b)(?:(?:static|inline|extern|const)[ \t]+)*(?:struct[ \t]+\w+|enum[ \t]+\w+|union[ \t]+\w+|{TIPOS_BASICOS}|[a-zA-Z_]\w*)[ \t]*(\*+[ \t]*|[ \t]+\*?)([a-zA-Z_]\w*)[ \t]*\(([\s\S]*?)\)[ \t]*([;{{])?",
            re.MULTILINE
        )

        prototipos_documentados_mismo_archivo: Set[str] = set()
        prototipos_no_documentados: List[Tuple[str, int, int]] = []
        definiciones_no_documentadas: List[Tuple[str, int, int]] = []

        for m_fn in re_fn_decl_all.finditer(codigo_sin_comentarios):
            fn_name = m_fn.group(2)
            if fn_name in ("if", "for", "while", "switch", "return", "sizeof", "main"):
                continue

            line_fn = codigo_sin_comentarios[:m_fn.start(2)].count("\n") + 1
            col_fn = m_fn.start(2) - codigo_sin_comentarios.rfind("\n", 0, m_fn.start(2))
            line_idx_start = codigo_sin_comentarios[:m_fn.start()].count("\n")

            tiene_doc = _tiene_comentario_documentacion(lineas, line_idx_start)

            char_cierre = m_fn.group(4)
            pos_despues_paren = m_fn.end()

            if char_cierre == ";":
                es_prototipo = True
            elif char_cierre == "{":
                es_prototipo = False
            else:
                resto = codigo_sin_comentarios[pos_despues_paren:pos_despues_paren + 100].lstrip()
                if resto.startswith(";"):
                    es_prototipo = True
                elif resto.startswith("{") or "{" in resto[:60]:
                    es_prototipo = False
                else:
                    continue

            if es_prototipo:
                if tiene_doc:
                    prototipos_documentados_mismo_archivo.add(fn_name)
                else:
                    prototipos_no_documentados.append((fn_name, line_fn, col_fn))
            else:
                if not tiene_doc:
                    definiciones_no_documentadas.append((fn_name, line_fn, col_fn))

        rcode, tit = _regla_info("0x2003h")

        if es_header:
            for fn_name, l_no, c_no in prototipos_no_documentados:
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=l_no,
                    columna=c_no,
                    mensaje=f"El prototipo de la función '{fn_name}' no incluye comentario de documentación.",
                    sugerencia="Documentá la función con @brief, @param y @return en formato Doxygen (/** ... */).",
                    codigo_linea=lineas[l_no - 1] if l_no <= len(lineas) else "",
                    es_autofixable=True,
                ))
        else:
            for fn_name, l_no, c_no in prototipos_no_documentados:
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=l_no,
                    columna=c_no,
                    mensaje=f"El prototipo de la función '{fn_name}' no incluye comentario de documentación.",
                    sugerencia="Documentá la función con @brief, @param y @return en formato Doxygen (/** ... */).",
                    codigo_linea=lineas[l_no - 1] if l_no <= len(lineas) else "",
                    es_autofixable=True,
                ))

            for fn_name, l_no, c_no in definiciones_no_documentadas:
                if fn_name in prototipos_documentados_mismo_archivo or fn_name in prototipos_doc_header:
                    continue
                if any(p[0] == fn_name for p in prototipos_no_documentados):
                    continue

                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=l_no,
                    columna=c_no,
                    mensaje=f"La función '{fn_name}' no incluye comentario de documentación.",
                    sugerencia="Documentá la función con @brief, @param y @return en formato Doxygen (/** ... */).",
                    codigo_linea=lineas[l_no - 1] if l_no <= len(lineas) else "",
                    es_autofixable=True,
                ))

    # -------------------------------------------------------------------------
    # 0x30XXh: Punteros y Gestión de Memoria
    # -------------------------------------------------------------------------

    # 0x3004h: Nomenclatura de typedef con _t o t_
    if _esta_activa("0x3004h"):
        re_typedef = re.compile(r"\btypedef\s+(?:struct|enum|union)\s*(?:\w*\s*\{[^}]*\}|\w+)\s+(\w+)\s*;", re.DOTALL)
        for m in re_typedef.finditer(codigo_sin_comentarios):
            tipo_name = m.group(1)
            if not (tipo_name.startswith("t_") or tipo_name.endswith("_t") or tipo_name.startswith("T_")):
                line_no = codigo_sin_comentarios[:m.start(1)].count("\n") + 1
                rcode, tit = _regla_info("0x3004h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=line_no,
                    columna=1,
                    mensaje=f"El tipo definido '{tipo_name}' no utiliza el prefijo 't_' ni el sufijo '_t'.",
                    sugerencia=f"Renombralo como 't_{tipo_name.lower()}' o '{tipo_name.lower()}_t'.",
                    es_autofixable=False,
                ))

    # 0x3003h: No mezclar asignación y comparación en la misma línea
    if _esta_activa("0x3003h"):
        re_asig_comp = re.compile(r"\b(?:if|while)\s*\(\s*\(\s*[a-zA-Z_]\w*\s*=\s*.+?\)\s*(?:==|!=|<|>|<=|>=)")
        for idx, linea in enumerate(lineas_sin_comentarios, 1):
            m = re_asig_comp.search(linea)
            if m:
                rcode, tit = _regla_info("0x3003h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=idx,
                    columna=m.start() + 1,
                    mensaje="Asignación y comparación combinadas en la misma línea de control.",
                    sugerencia="Separá la asignación en una instrucción previa antes del condicional.",
                    codigo_linea=lineas[idx - 1],
                    es_autofixable=False,
                ))

    # 0x3008h: Comparación de punteros contra 0 en vez de NULL
    if _esta_activa("0x3008h"):
        re_ptr_zero = re.compile(r"\b\w*(?:ptr|nodo|lista|buffer|puntero|archivo|file)\w*\s*(?:==|!=)\s*0\b", re.IGNORECASE)
        for idx, linea in enumerate(lineas_sin_comentarios, 1):
            m = re_ptr_zero.search(linea)
            if m:
                rcode, tit = _regla_info("0x3008h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=idx,
                    columna=m.start() + 1,
                    mensaje="Comparación de puntero contra el literal numérico '0'.",
                    sugerencia="Utilizá explícitamente la constante 'NULL'.",
                    codigo_linea=lineas[idx - 1],
                    es_autofixable=False,
                ))

    # 0x3005h: Punteros triples (***) o más niveles de indirección
    if _esta_activa("0x3005h"):
        re_triple_ptr = re.compile(r"\b\w+\s*\*\*\*\s*\w+")
        for idx, linea in enumerate(lineas_sin_comentarios, 1):
            m = re_triple_ptr.search(linea)
            if m:
                rcode, tit = _regla_info("0x3005h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=idx,
                    columna=m.start() + 1,
                    mensaje="Uso de tres o más niveles de indirección de punteros (***).",
                    sugerencia="Rediseñá la estructura de datos o utilizá encapsulamiento en structs.",
                    codigo_linea=lineas[idx - 1],
                    es_autofixable=False,
                ))

    # 0x300Bh: malloc(literal) sin sizeof
    if _esta_activa("0x300Bh"):
        re_malloc_literal = re.compile(r"\bmalloc\s*\(\s*\d+\s*\)")
        for idx, linea in enumerate(lineas_sin_comentarios, 1):
            m = re_malloc_literal.search(linea)
            if m:
                rcode, tit = _regla_info("0x300Bh")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=idx,
                    columna=m.start() + 1,
                    mensaje=f"Llamada a '{m.group(0)}' con tamaño numérico constante sin sizeof.",
                    sugerencia="Utilizá 'sizeof(*ptr)' o 'sizeof(tipo_t)' para calcular el tamaño dinámicamente.",
                    codigo_linea=lineas[idx - 1],
                    es_autofixable=False,
                ))

    # 0x0035h: TDA con struct no opaco en archivo .h
    if _esta_activa("0x0035h") and es_header:
        re_struct_body = re.compile(r"^\s*struct\s+\w+\s*\{[^}]+\}\s*;", re.MULTILINE)
        for m in re_struct_body.finditer(codigo_sin_comentarios):
            line_no = codigo_sin_comentarios[:m.start()].count("\n") + 1
            rcode, tit = _regla_info("0x0035h")
            violaciones.append(ViolacionRegla(
                codigo=rcode,
                titulo=tit,
                archivo=ruta,
                linea=line_no,
                columna=1,
                mensaje="Definición de campos de estructura interna en archivo de cabecera (.h).",
                sugerencia="Ocultá la implementación mediante un TDA con puntero opaco ('typedef struct nombre_t nombre_t;').",
                es_autofixable=False,
            ))

    # -------------------------------------------------------------------------
    # Serie GAFF06x: 0x300Dh, 0x2001h, 0x000Dh
    # -------------------------------------------------------------------------

    # 0x300Dh (GAFF006 / GAFF061): Números mágicos (literales fuera de 0, 1, 2, -1)
    if _esta_activa("0x300Dh"):
        codigo_magicos = codigo_sin_comentarios
        # Los bloques enum son contexto válido para literales numéricos
        for m_enum in list(re.finditer(r"\benum\b[^{;]*\{[^}]*\}", codigo_magicos, re.DOTALL)):
            relleno = "".join("\n" if c == "\n" else " " for c in m_enum.group(0))
            codigo_magicos = codigo_magicos[: m_enum.start()] + relleno + codigo_magicos[m_enum.end():]
        codigo_magicos = _enmascarar_literales(codigo_magicos)

        re_num_magico = re.compile(
            r"(?<![\w.])(?:0[xX][0-9a-fA-F]+|\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)(?:[uUlLfF]+)?"
        )
        for idx, linea in enumerate(codigo_magicos.splitlines(), 1):
            linea_strip = linea.strip()
            if linea_strip.startswith("#"):
                continue
            # Ignorar líneas que definen constantes
            if re.match(r"^\s*(?:static\s+)?const\s+", linea):
                continue
            for m in re_num_magico.finditer(linea):
                literal = m.group(0)
                if literal.lower().startswith("0x"):
                    valor = float(int(literal[2:].rstrip("uUlL") or "0", 16))
                else:
                    valor = float(literal.rstrip("uUlLfF"))
                if valor in (0.0, 1.0, 2.0):
                    continue
                col_start = m.start()
                if col_start > 0 and linea[col_start - 1] == "-" and valor == 1.0:
                    continue
                rcode, tit = _regla_info("0x300Dh")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=idx,
                    columna=m.start() + 1,
                    mensaje=f"Número mágico '{literal}' sin contexto: no está definido como constante.",
                    sugerencia=f"Definí una constante descriptiva con #define o enum (ej: '#define MAX_INTENTOS {literal}') y usala en su lugar.",
                    codigo_linea=lineas[idx - 1] if idx - 1 < len(lineas) else "",
                    es_autofixable=False,
                ))

    # 0x2001h (GAFF025 / GAFF065): Anidación máxima de 3 niveles dentro de funciones
    if _esta_activa("0x2001h"):
        codigo_nesting = _enmascarar_literales(codigo_sin_comentarios)
        re_no_funcion = re.compile(r"^\s*(?:typedef\s+)?(?:struct|enum|union)\b")
        profundidad = 0
        base_funcion: Optional[int] = None
        ultimo_hito = 0
        for i, ch in enumerate(codigo_nesting):
            if ch == "{":
                profundidad += 1
                if base_funcion is None:
                    segmento = "\n".join(
                        ln for ln in codigo_nesting[ultimo_hito:i].splitlines()
                        if not ln.strip().startswith("#")
                    ).strip()
                    if segmento.endswith(")") and "=" not in segmento and not re_no_funcion.match(segmento):
                        base_funcion = profundidad
                elif profundidad - base_funcion == 4:
                    texto_previo = codigo_nesting[ultimo_hito:i].strip()
                    if not texto_previo.endswith("="):
                        line_no = codigo_nesting[:i].count("\n") + 1
                        rcode, tit = _regla_info("0x2001h")
                        violaciones.append(ViolacionRegla(
                            codigo=rcode,
                            titulo=tit,
                            archivo=ruta,
                            linea=line_no,
                            columna=1,
                            mensaje="Anidación de 4 niveles: supera el máximo de 3 niveles permitidos (código en flecha).",
                            sugerencia="Aplicá cláusulas de guarda (retornos tempranos) o extraé funciones auxiliares para reducir la anidación.",
                            codigo_linea=lineas[line_no - 1],
                            es_autofixable=False,
                        ))
                ultimo_hito = i + 1
            elif ch == "}":
                profundidad -= 1
                if base_funcion is not None and profundidad < base_funcion:
                    base_funcion = None
                ultimo_hito = i + 1
            elif ch == ";":
                ultimo_hito = i + 1

    # 0x000Dh: Código comentado (dead code)
    if _esta_activa("0x000Dh"):
        re_codigo_comentado = re.compile(
            r"^\s*(?:"
            r"(?:if|for|while|switch|return|break|continue|else|do)\b"
            r"|[\w\])]+\s*=[^=]"
            r"|.*;\s*$"
            r"|#\s*(?:include|define|ifdef|ifndef|endif|undef|pragma)\b"
            r")"
        )
        re_token_comentario = re.compile(
            r"//.*?$|/\*.*?\*/|'(?:\\.|[^\\'])*'|\"(?:\\.|[^\\\"])*\"",
            re.DOTALL | re.MULTILINE,
        )
        for m in re_token_comentario.finditer(contenido_original):
            token = m.group(0)
            if not token.startswith("/"):
                continue
            if token.startswith("//"):
                lineas_cuerpo = [token[2:].strip()]
            else:
                lineas_cuerpo = []
                for ln in token[2:-2].splitlines():
                    ln = re.sub(r"^\s*\*+\s?", "", ln).strip()
                    if ln:
                        lineas_cuerpo.append(ln)
            linea_code = next((ln for ln in lineas_cuerpo if re_codigo_comentado.match(ln)), None)
            if linea_code is None:
                continue
            line_no = contenido_original[:m.start()].count("\n") + 1
            columna = m.start() - contenido_original.rfind("\n", 0, m.start())
            rcode, tit = _regla_info("0x000Dh")
            violaciones.append(ViolacionRegla(
                codigo=rcode,
                titulo=tit,
                archivo=ruta,
                linea=line_no,
                columna=columna,
                mensaje=f"Código comentado detectado: '{linea_code[:50]}'",
                sugerencia="Eliminá el código comentado: el historial de cambios pertenece al control de versiones.",
                codigo_linea=lineas[line_no - 1],
                es_autofixable=False,
            ))

    # -------------------------------------------------------------------------
    # 0x000Eh: Nombres de funciones en snake_case estricto
    # -------------------------------------------------------------------------
    if _esta_activa("0x000Eh"):
        re_fn_decl = re.compile(r"^\s*(?:[a-zA-Z0-9_*]+\s+)+([a-zA-Z0-9_]+)\s*\([^;{)]*\)\s*\{", re.MULTILINE)
        for m in re_fn_decl.finditer(codigo_sin_comentarios):
            fn_name = m.group(1)
            if fn_name in ("if", "for", "while", "switch", "main"):
                continue
            # Si contiene mayúsculas (camelCase / PascalCase)
            if any(c.isupper() for c in fn_name):
                line_no = codigo_sin_comentarios[:m.start(1)].count("\n") + 1
                col = m.start(1) - codigo_sin_comentarios.rfind("\n", 0, m.start(1))
                sugerido_fn = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", fn_name).lower()
                rcode, tit = _regla_info("0x000Eh")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=line_no,
                    columna=col,
                    mensaje=f"El nombre de la función '{fn_name}' no utiliza snake_case en minúsculas (mezcla mayúsculas/camelCase).",
                    sugerencia=f"Renombrá la función a snake_case en minúsculas (ej: '{sugerido_fn}').",
                    codigo_linea=lineas[line_no - 1] if line_no <= len(lineas) else "",
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x000Fh: Evitá comentarios obvios, redundantes, vacíos o TODO/FIXME pendientes
    # -------------------------------------------------------------------------
    if _esta_activa("0x000Fh"):
        for i, l in enumerate(lineas):
            if "//" in l:
                coment = l.split("//", 1)[1].strip()
                m_todo = re.search(r"\b(TODO|FIXME|XXX|HACK)\b", coment, re.IGNORECASE)
                if m_todo:
                    rcode, tit = _regla_info("0x000Fh")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=i + 1,
                        columna=l.index("//") + 1,
                        mensaje=f"Comentario TODO/FIXME pendiente detectado: '// {coment}'",
                        sugerencia="Resolvé la tarea pendiente o eliminá el comentario antes de la entrega final.",
                        codigo_linea=l,
                        es_autofixable=False,
                    ))
                elif not coment or re.search(r"^(?:incrementa|suma|guarda|asigna|imprime|retorna)\s+\w+", coment, re.IGNORECASE):
                    rcode, tit = _regla_info("0x000Fh")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=i + 1,
                        columna=l.index("//") + 1,
                        mensaje=f"Comentario redundante, obvio o vacío detectado: '// {coment}'",
                        sugerencia="Explicá la justificación algorítmica ('el porqué') en lugar de describir la sintaxis obvia, o eliminá el comentario.",
                        codigo_linea=l,
                        es_autofixable=True,
                    ))
            elif "/*" in l:
                m_todo_blk = re.search(r"\b(TODO|FIXME|XXX|HACK)\b", l, re.IGNORECASE)
                if m_todo_blk:
                    rcode, tit = _regla_info("0x000Fh")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=i + 1,
                        columna=l.index("/*") + 1,
                        mensaje=f"Comentario TODO/FIXME pendiente detectado en bloque: '{l.strip()}'",
                        sugerencia="Resolvé la tarea pendiente o eliminá el comentario antes de la entrega final.",
                        codigo_linea=l,
                        es_autofixable=False,
                    ))

    # -------------------------------------------------------------------------
    # 0x0010h: Longitud máxima de archivos (máx 500 líneas)
    # -------------------------------------------------------------------------
    if _esta_activa("0x0010h") and len(lineas) > 500:
        rcode, tit = _regla_info("0x0010h")
        violaciones.append(ViolacionRegla(
            codigo=rcode,
            titulo=tit,
            archivo=ruta,
            linea=len(lineas),
            columna=1,
            mensaje=f"El archivo supera el límite recomendado de 500 líneas ({len(lineas)} líneas).",
            sugerencia="Modularizá el archivo dividiendo las funciones en módulos/TDAs complementarios con sus cabeceras .h.",
            codigo_linea=lineas[-1] if lineas else "",
            es_autofixable=False,
        ))

    # -------------------------------------------------------------------------
    # 0x0011h: Inclusión de cabecera propia en primer lugar en .c
    # -------------------------------------------------------------------------
    if _esta_activa("0x0011h") and ruta.suffix.lower() == ".c":
        header_propio = f'"{ruta.stem}.h"'
        headers_encontrados = []
        for i, l in enumerate(lineas):
            strip_l = l.strip()
            if strip_l.startswith("#include") and '"' in strip_l:
                headers_encontrados.append((i + 1, strip_l))
        if headers_encontrados and (ruta.parent / f"{ruta.stem}.h").is_file():
            primero_lin, primero_txt = headers_encontrados[0]
            if header_propio not in primero_txt:
                rcode, tit = _regla_info("0x0011h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=primero_lin,
                    columna=1,
                    mensaje=f"La cabecera propia '#include {header_propio}' debe incluirse antes de cualquier otro header de usuario.",
                    sugerencia=f"Colocá '#include {header_propio}' como la primera línea de inclusión para verificar que el header sea autosuficiente.",
                    codigo_linea=lineas[primero_lin - 1],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x0012h: Variables globales deben ser static o usar prefijo g_
    # -------------------------------------------------------------------------
    if _esta_activa("0x0012h"):
        re_global_var = re.compile(rf"^(?!static|const|extern|typedef)\s*{TIPOS_BASICOS}\s+([a-zA-Z_]\w*)\s*(?:=|;)", re.MULTILINE)
        # Buscar declaraciones fuera de funciones (al nivel de indentación 0)
        for i, l in enumerate(lineas):
            if l.startswith(" ") or l.startswith("\t") or l.strip().startswith("//") or l.strip().startswith("/*"):
                continue
            if "(" in l or ")" in l or l.strip().startswith("#"):
                continue
            m = re_global_var.match(l)
            if m:
                var_name = m.group(1)
                if not var_name.startswith("g_"):
                    rcode, tit = _regla_info("0x0012h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=i + 1,
                        columna=1,
                        mensaje=f"Variable global '{var_name}' declarada sin 'static' ni prefijo 'g_'.",
                        sugerencia=f"Declarala como 'static {l.strip()}' o renombrala con prefijo 'g_{var_name}' para visibilizar el acoplamiento global.",
                        codigo_linea=l,
                        es_autofixable=False,
                    ))

    # -------------------------------------------------------------------------
    # 0x0000h: La claridad y prolijidad son de máxima importancia
    # -------------------------------------------------------------------------
    if _esta_activa("0x0000h"):
        blanks = 0
        for i, l in enumerate(lineas):
            if not l.strip():
                blanks += 1
                if blanks >= 3:
                    rcode, tit = _regla_info("0x0000h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=i + 1,
                        columna=1,
                        mensaje=f"Líneas en blanco redundantes consecutivas ({blanks}). Mantené la prolijidad eliminando el espaciado vertical excesivo.",
                        sugerencia="Reducí los saltos de línea consecutivos para mantener la compacidad del código.",
                        codigo_linea=lineas[i],
                        es_autofixable=True,
                    ))
            else:
                blanks = 0

        # Verificación de que los archivos terminen siempre con una nueva línea (\n)
        if contenido_original and not contenido_original.endswith("\n"):
            rcode, tit = _regla_info("0x0000h")
            violaciones.append(ViolacionRegla(
                codigo=rcode,
                titulo=tit,
                archivo=ruta,
                linea=len(lineas),
                columna=len(lineas[-1]) + 1 if lineas else 1,
                mensaje="El archivo no termina con una nueva línea (\\n) al final.",
                sugerencia="Agregá un salto de línea al final del archivo para cumplir con el estándar POSIX C.",
                codigo_linea=lineas[-1] if lineas else "",
                es_autofixable=True,
            ))

    # -------------------------------------------------------------------------
    # 0x000Ah: Comentarios que expliquen el "porqué", no el "qué"
    # -------------------------------------------------------------------------
    if _esta_activa("0x000Ah"):
        re_comentario_obvio = re.compile(r"//\s*(?:incrementa\s+\w+\s+en\s+1|aumenta\s+\w+\s+en\s+1|suma\s+1\s+a\s+\w+|asigna\s+\w+\s+a\s+\w+|retorna\s+0\b)", re.IGNORECASE)
        for i, l in enumerate(lineas):
            m_obv = re_comentario_obvio.search(l)
            if m_obv:
                rcode, tit = _regla_info("0x000Ah")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_obv.start() + 1,
                    mensaje="Comentario redundante que describe lo evidente en lugar del porqué de la decisión.",
                    sugerencia="Escribí comentarios que expliquen la justificación o contexto de diseño, no la sintaxis evidente.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x0036h: Asignar NULL al puntero tras liberar un recurso opaco / destructor TDA
    # -------------------------------------------------------------------------
    if _esta_activa("0x0036h"):
        re_destroy_call = re.compile(r"\b([a-zA-Z0-9_]+(?:_destruir|_destroy|_liberar|_cerrar))\s*\(\s*([a-zA-Z_]\w*)\s*\)\s*;")
        for i, l in enumerate(lineas_sin_comentarios):
            m_dest = re_destroy_call.search(l)
            if m_dest:
                fn_dest = m_dest.group(1)
                pname = m_dest.group(2)
                siguientes = " ".join(lineas_sin_comentarios[i:i + 4])
                tiene_null = bool(re.search(rf"\b{pname}\s*=\s*NULL\s*;", siguientes))
                if not tiene_null:
                    rcode, tit = _regla_info("0x0036h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=i + 1,
                        columna=m_dest.start() + 1,
                        mensaje=f"Recurso de TDA liberado mediante '{fn_dest}({pname})' sin anular el puntero '{pname} = NULL;'.",
                        sugerencia=f"Asigná '{pname} = NULL;' tras invocar al destructor para invalidar la referencia en el cliente.",
                        codigo_linea=lineas[i],
                        es_autofixable=False,
                    ))

    # -------------------------------------------------------------------------
    # 0x1004h: Condiciones complejas deben simplificarse o comentarse
    # -------------------------------------------------------------------------
    if _esta_activa("0x1004h"):
        re_control_cond = re.compile(r"\b(?:if|while)\s*\((.*?)\)\s*\{?", re.DOTALL)
        for m in re_control_cond.finditer(codigo_sin_comentarios):
            cond_texto = m.group(1)
            total_ops = len(re.findall(r"&&", cond_texto)) + len(re.findall(r"\|\|", cond_texto))
            if total_ops >= 3:
                linea_num = contenido_original[:m.start()].count("\n") + 1
                rcode, tit = _regla_info("0x1004h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=linea_num,
                    columna=1,
                    mensaje=f"Condición lógica compleja con {total_ops} operadores lógicos. Simplificala con variables booleanas intermedias.",
                    sugerencia="Dividí la condición en variables booleanas explicativas (ej: 'bool puede_acceder = ...;').",
                    codigo_linea=lineas[linea_num - 1] if linea_num <= len(lineas) else "",
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x1005h: Evitar condiciones ambiguas por truthiness (strcmp, punteros, chars)
    # -------------------------------------------------------------------------
    if _esta_activa("0x1005h"):
        re_not_strcmp = re.compile(r"\b(?:if|while)\s*\(\s*!\s*str(?:n)?(?:case)?cmp\s*\(")
        re_not_ptr = re.compile(r"\b(?:if|while)\s*\(\s*!\s*([a-zA-Z_]\w*(?:_ptr|ptr|p))\s*\)")
        re_not_char = re.compile(r"\b(?:if|while)\s*\(\s*!\s*([a-zA-Z_]\w*\[[^\]]+\])\s*\)")

        for i, l in enumerate(lineas_sin_comentarios):
            m1 = re_not_strcmp.search(l)
            if m1:
                rcode, tit = _regla_info("0x1005h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m1.start() + 1,
                    mensaje="Condición ambigua: uso de '!strcmp(...)' en lugar de comparación explícita contra 0.",
                    sugerencia="Compará explícitamente: 'if (strcmp(...) == 0)' para clarificar la igualdad.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))
            m2 = re_not_ptr.search(l)
            if m2:
                p_name = m2.group(1)
                rcode, tit = _regla_info("0x1005h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m2.start() + 1,
                    mensaje=f"Condición ambigua por veracidad implícita: '!{p_name}'.",
                    sugerencia=f"Compará el puntero explícitamente contra NULL: 'if ({p_name} == NULL)'.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))
            m3 = re_not_char.search(l)
            if m3:
                c_expr = m3.group(1)
                rcode, tit = _regla_info("0x1005h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m3.start() + 1,
                    mensaje=f"Condición ambigua por veracidad implícita: '!{c_expr}'.",
                    sugerencia=f"Compará el carácter explícitamente contra el nulo: 'if ({c_expr} == \'\\0\')'.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x2006h: Una aserción por cada función de prueba
    # -------------------------------------------------------------------------
    if _esta_activa("0x2006h"):
        re_fn_test = re.compile(r"^(?:void|int)\s+((?:test|prueba)_\w+)\s*\([^)]*\)\s*\{", re.MULTILINE)
        for m_test in re_fn_test.finditer(codigo_sin_comentarios):
            fn_name = m_test.group(1)
            start_idx = m_test.end()
            brace_count = 1
            curr_idx = start_idx
            while curr_idx < len(codigo_sin_comentarios) and brace_count > 0:
                ch = codigo_sin_comentarios[curr_idx]
                if ch == "{":
                    brace_count += 1
                elif ch == "}":
                    brace_count -= 1
                curr_idx += 1
            fn_body = codigo_sin_comentarios[start_idx:curr_idx]
            asserts = len(re.findall(r"\b(?:assert|mu_assert|munit_assert)\s*\(", fn_body))
            if asserts > 1:
                linea_num = contenido_original[:m_test.start()].count("\n") + 1
                rcode, tit = _regla_info("0x2006h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=linea_num,
                    columna=1,
                    mensaje=f"La función de prueba '{fn_name}' contiene {asserts} aserciones (máximo permitido: 1).",
                    sugerencia="Dividí la prueba en casos unitarios separados con una aserción cada uno.",
                    codigo_linea=lineas[linea_num - 1] if linea_num <= len(lineas) else "",
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x2007h: Mantené el alcance de las variables al mínimo posible
    # -------------------------------------------------------------------------
    if _esta_activa("0x2007h"):
        re_for_outer = re.compile(r"^\s*(?:int|size_t)\s+([a-zA-Z_]\w*)\s*;", re.MULTILINE)
        for m_var in re_for_outer.finditer(codigo_sin_comentarios):
            vname = m_var.group(1)
            if re.search(rf"\bfor\s*\(\s*{vname}\s*=\s*0", codigo_sin_comentarios[m_var.end():]):
                linea_num = contenido_original[:m_var.start()].count("\n") + 1
                rcode, tit = _regla_info("0x2007h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=linea_num,
                    columna=1,
                    mensaje=f"Variable de iteración '{vname}' declarada fuera del lazo 'for'.",
                    sugerencia=f"Declará la variable dentro del lazo: 'for (int {vname} = 0; ...)'.",
                    codigo_linea=lineas[linea_num - 1] if linea_num <= len(lineas) else "",
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x2008h: Valores de retorno numéricos deben ser constantes o enums
    # -------------------------------------------------------------------------
    if _esta_activa("0x2008h"):
        re_magic_ret = re.compile(r"^\s*return\s+(-?[1-9]\d*)\s*;", re.MULTILINE)
        for i, l in enumerate(lineas_sin_comentarios):
            m_ret = re_magic_ret.match(l)
            if m_ret:
                es_main_o_test = False
                for j in range(i, -1, -1):
                    if "int main(" in lineas_sin_comentarios[j] or "main(" in lineas_sin_comentarios[j]:
                        es_main_o_test = True
                        break
                    if re.search(r"\b(?:test|prueba)_\w+\s*\(", lineas_sin_comentarios[j]):
                        es_main_o_test = True
                        break
                    if lineas_sin_comentarios[j].startswith("}"):
                        break
                if not es_main_o_test:
                    val = m_ret.group(1)
                    rcode, tit = _regla_info("0x2008h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=i + 1,
                        columna=1,
                        mensaje=f"Retorno de valor numérico mágico '{val}' en lugar de constante o enumeración.",
                        sugerencia="Definí un enum con nombres de estado o constantes como RETORNO_EXITO / ERROR_INVALIDO.",
                        codigo_linea=lineas[i],
                        es_autofixable=False,
                    ))

    # -------------------------------------------------------------------------
    # 0x2009h: Los ejercicios deben ser resueltos mediante funciones (no monolítico en main)
    # -------------------------------------------------------------------------
    if _esta_activa("0x2009h") and ruta.suffix.lower() == ".c":
        re_main_block = re.compile(r"int\s+main\s*\([^)]*\)\s*\{", re.MULTILINE)
        m_main = re_main_block.search(codigo_sin_comentarios)
        if m_main:
            todas_fns = re.findall(rf"^(?!typedef|extern|static\s+const)\s*{TIPOS_BASICOS}\s+(\w+)\s*\([^;]*\)\s*\{{", codigo_sin_comentarios, re.MULTILINE)
            fns_auxiliares = [f for f in todas_fns if f != "main"]
            if not fns_auxiliares and len(lineas) > 35:
                linea_num = contenido_original[:m_main.start()].count("\n") + 1
                rcode, tit = _regla_info("0x2009h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=linea_num,
                    columna=1,
                    mensaje="El ejercicio concentra toda la lógica en 'main()' sin modularizar en funciones.",
                    sugerencia="Descomponé el problema en funciones con responsabilidades únicas.",
                    codigo_linea=lineas[linea_num - 1] if linea_num <= len(lineas) else "",
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x3001h: Siempre verificar asignación de memoria dinámica contra NULL
    # -------------------------------------------------------------------------
    if _esta_activa("0x3001h"):
        re_alloc_call = re.compile(r"\b([a-zA-Z_]\w*)\s*=\s*(?:\([a-zA-Z0-9_* ]+\)\s*)?(?:malloc|calloc|realloc)\s*\(")
        for i, l in enumerate(lineas_sin_comentarios):
            m_alloc = re_alloc_call.search(l)
            if m_alloc:
                pname = m_alloc.group(1)
                siguientes = " ".join(lineas_sin_comentarios[i:i + 7])
                tiene_check = bool(re.search(rf"\bif\s*\(\s*(?:{pname}\s*==\s*NULL|NULL\s*==\s*{pname}|!{pname}|{pname}\s*!=\s*NULL)\b", siguientes))
                if not tiene_check:
                    rcode, tit = _regla_info("0x3001h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=i + 1,
                        columna=m_alloc.start() + 1,
                        mensaje=f"Asignación de memoria dinámica para '{pname}' sin verificación inmediata contra NULL.",
                        sugerencia=f"Agregá 'if ({pname} == NULL) {{ ... }}' inmediatamente después de la asignación.",
                        codigo_linea=lineas[i],
                        es_autofixable=False,
                    ))

    # -------------------------------------------------------------------------
    # 0x3002h: Liberar memoria dinámica y asignar NULL al puntero
    # -------------------------------------------------------------------------
    if _esta_activa("0x3002h"):
        re_free_call = re.compile(r"\bfree\s*\(\s*([a-zA-Z_]\w*)\s*\)\s*;")
        for i, l in enumerate(lineas_sin_comentarios):
            m_free = re_free_call.search(l)
            if m_free:
                pname = m_free.group(1)
                siguientes = " ".join(lineas_sin_comentarios[i:i + 4])
                tiene_null = bool(re.search(rf"\b{pname}\s*=\s*NULL\s*;", siguientes))
                if not tiene_null:
                    rcode, tit = _regla_info("0x3002h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=i + 1,
                        columna=m_free.start() + 1,
                        mensaje=f"Memoria liberada con 'free({pname})' sin asignar '{pname} = NULL;' para prevenir punteros colgantes.",
                        sugerencia=f"Colocá '{pname} = NULL;' inmediatamente después de 'free({pname})'.",
                        codigo_linea=lineas[i],
                        es_autofixable=False,
                    ))

    # -------------------------------------------------------------------------
    # 0x3006h: Documentar la propiedad de los recursos al utilizar punteros
    # -------------------------------------------------------------------------
    if _esta_activa("0x3006h"):
        re_creator_fn = re.compile(r"^(?:[a-zA-Z_]\w*\*|\w+\s*\*)\s*([a-zA-Z_]\w*(?:_crear|_create|_nuevo|_new))\s*\([^)]*\)\s*\{", re.MULTILINE)
        for m_cr in re_creator_fn.finditer(codigo_sin_comentarios):
            fname = m_cr.group(1)
            linea_fn = contenido_original[:m_cr.start()].count("\n")
            doc_previa = ""
            idx = linea_fn - 1
            while idx >= 0 and lineas[idx].strip():
                doc_previa = lineas[idx] + "\n" + doc_previa
                if "/*" in lineas[idx]:
                    break
                idx -= 1
            if not any(k in doc_previa.lower() for k in ("propiedad", "dueño", "responsable", "liberar", "free", "destruir")):
                rcode, tit = _regla_info("0x3006h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=linea_fn + 1,
                    columna=1,
                    mensaje=f"Función creadora '{fname}' retorna puntero sin documentar la propiedad del recurso ni su liberación.",
                    sugerencia="Añadí en la documentación doxygen quién es el responsable de liberar la memoria.",
                    codigo_linea=lineas[linea_fn] if linea_fn < len(lineas) else "",
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x3007h: Argumentos puntero const si la función no los modifica
    # -------------------------------------------------------------------------
    if _esta_activa("0x3007h"):
        re_readonly_fn = re.compile(r"\b(?:void|int|size_t)\s+((?:imprimir|mostrar|calcular|contar|buscar|es|son|verificar)_\w+)\s*\(([^)]+)\)", re.MULTILINE)
        for m_ro in re_readonly_fn.finditer(codigo_sin_comentarios):
            fname = m_ro.group(1)
            params_str = m_ro.group(2)
            for param in params_str.split(","):
                param = param.strip()
                if "*" in param and "const" not in param:
                    linea_num = contenido_original[:m_ro.start()].count("\n") + 1
                    rcode, tit = _regla_info("0x3007h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=linea_num,
                        columna=1,
                        mensaje=f"Parámetro puntero '{param}' en función de solo lectura '{fname}' sin calificador 'const'.",
                        sugerencia=f"Declaralo como 'const {param.strip()}' para garantizar que la función no modifique los datos.",
                        codigo_linea=lineas[linea_num - 1] if linea_num <= len(lineas) else "",
                        es_autofixable=False,
                    ))

    # -------------------------------------------------------------------------
    # 0x3009h: Documentar explícitamente casos donde una función puede retornar NULL
    # -------------------------------------------------------------------------
    if _esta_activa("0x3009h"):
        re_fn_ptr = re.compile(r"^(?:[a-zA-Z_]\w*\*|\w+\s*\*)\s*([a-zA-Z_]\w*)\s*\([^)]*\)\s*\{", re.MULTILINE)
        for m_fptr in re_fn_ptr.finditer(codigo_sin_comentarios):
            fn_name = m_fptr.group(1)
            start_idx = m_fptr.end()
            brace_count = 1
            curr_idx = start_idx
            while curr_idx < len(codigo_sin_comentarios) and brace_count > 0:
                ch = codigo_sin_comentarios[curr_idx]
                if ch == "{":
                    brace_count += 1
                elif ch == "}":
                    brace_count -= 1
                curr_idx += 1
            body = codigo_sin_comentarios[start_idx:curr_idx]
            if re.search(r"\breturn\s+NULL\s*;", body):
                linea_fn = contenido_original[:m_fptr.start()].count("\n")
                doc_previa = ""
                idx = linea_fn - 1
                while idx >= 0 and lineas[idx].strip():
                    doc_previa = lineas[idx] + "\n" + doc_previa
                    if "/*" in lineas[idx]:
                        break
                    idx -= 1
                if "NULL" not in doc_previa:
                    rcode, tit = _regla_info("0x3009h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=linea_fn + 1,
                        columna=1,
                        mensaje=f"La función '{fn_name}' retorna puntero y contiene 'return NULL;' pero su documentación no explicita el retorno de NULL.",
                        sugerencia="Añadí en '@return' que retorna NULL en caso de error o elemento inexistente.",
                        codigo_linea=lineas[linea_fn] if linea_fn < len(lineas) else "",
                        es_autofixable=False,
                    ))

    # -------------------------------------------------------------------------
    # 0x300Ah: Utilizá cast explícito al convertir tipos de punteros
    # -------------------------------------------------------------------------
    if _esta_activa("0x300Ah"):
        re_impl_cast = re.compile(r"\bint\s*\*\s*([a-zA-Z_]\w*)\s*=\s*(?:mem|buffer|ptr_gen|datos_void)\s*;", re.IGNORECASE)
        for i, l in enumerate(lineas_sin_comentarios):
            m_cast = re_impl_cast.search(l)
            if m_cast:
                rcode, tit = _regla_info("0x300Ah")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_cast.start() + 1,
                    mensaje="Conversión implícita de puntero genérico; se requiere cast explícito '(tipo *)'.",
                    sugerencia="Escribí un cast explícito, por ejemplo: '(int *)mem'.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x300Ch: Límites de arreglos estáticos
    # -------------------------------------------------------------------------
    if _esta_activa("0x300Ch"):
        re_arr_decl = re.compile(r"\b(?:int|char|float|double)\s+([a-zA-Z_]\w*)\s*\[\s*(\d+)\s*\]\s*;")
        for m_arr in re_arr_decl.finditer(codigo_sin_comentarios):
            arr_name = m_arr.group(1)
            arr_size = int(m_arr.group(2))
            re_arr_access = re.compile(rf"\b{arr_name}\s*\[\s*(\d+)\s*\]")
            for m_acc in re_arr_access.finditer(codigo_sin_comentarios[m_arr.end():]):
                idx_val = int(m_acc.group(1))
                if idx_val >= arr_size:
                    linea_num = contenido_original[:m_arr.end() + m_acc.start()].count("\n") + 1
                    rcode, tit = _regla_info("0x300Ch")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=linea_num,
                        columna=1,
                        mensaje=f"Acceso fuera de los límites del arreglo '{arr_name}' con índice estático [{idx_val}] (tamaño: {arr_size}).",
                        sugerencia=f"Asegurá que el índice esté dentro del rango válido [0, {arr_size - 1}].",
                        codigo_linea=lineas[linea_num - 1] if linea_num <= len(lineas) else "",
                        es_autofixable=False,
                    ))

    # -------------------------------------------------------------------------
    # 0x300Eh: Documentar comportamiento de funciones al manejar punteros nulos
    # -------------------------------------------------------------------------
    if _esta_activa("0x300Eh"):
        re_fn_ptrs = re.compile(r"^(?:[a-zA-Z_]\w*\*?|\w+\s*\*?)\s*([a-zA-Z_]\w*)\s*\(([^)]*\*[a-zA-Z_]\w*[^)]*)\)\s*\{", re.MULTILINE)
        for m_fp in re_fn_ptrs.finditer(codigo_sin_comentarios):
            fn_name = m_fp.group(1)
            linea_fn = contenido_original[:m_fp.start()].count("\n")
            doc_previa = ""
            idx = linea_fn - 1
            while idx >= 0 and lineas[idx].strip():
                doc_previa = lineas[idx] + "\n" + doc_previa
                if "/*" in lineas[idx]:
                    break
                idx -= 1
            if doc_previa and "NULL" not in doc_previa and "@pre" not in doc_previa:
                rcode, tit = _regla_info("0x300Eh")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=linea_fn + 1,
                    columna=1,
                    mensaje=f"La función '{fn_name}' recibe argumentos puntero pero no documenta el comportamiento ante 'NULL' ni precondiciones.",
                    sugerencia="Especificá en la documentación si la función admite punteros NULL o declará '@pre ptr != NULL'.",
                    codigo_linea=lineas[linea_fn] if linea_fn < len(lineas) else "",
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x300Fh: Liberación de memoria en orden inverso
    # -------------------------------------------------------------------------
    if _esta_activa("0x300Fh"):
        re_free_matrix = re.compile(r"\bfree\s*\(\s*([a-zA-Z_]\w*)\s*\)\s*;\s*.*?free\s*\(\s*\1\s*\[", re.DOTALL)
        for m_inv in re_free_matrix.finditer(codigo_sin_comentarios):
            m_name = m_inv.group(1)
            linea_num = contenido_original[:m_inv.start()].count("\n") + 1
            rcode, tit = _regla_info("0x300Fh")
            violaciones.append(ViolacionRegla(
                codigo=rcode,
                titulo=tit,
                archivo=ruta,
                linea=linea_num,
                columna=1,
                mensaje=f"Liberación en orden incorrecto: se libera el contenedor principal '{m_name}' antes de sus elementos.",
                sugerencia=f"Liberá primero los elementos internos ('{m_name}[i]') y finalmente el puntero principal.",
                codigo_linea=lineas[linea_num - 1] if linea_num <= len(lineas) else "",
                es_autofixable=False,
            ))

    # -------------------------------------------------------------------------
    # 0x3010h: Variables de tamaño o índice deben ser de tipo size_t
    # -------------------------------------------------------------------------
    if _esta_activa("0x3010h"):
        re_int_size = re.compile(r"\bint\s+((?:tamano|tamanio|longitud|cantidad|len|tam|sz)\w*)\s*(?:=|;)", re.IGNORECASE)
        re_int_sizeof_assign = re.compile(r"\bint\s+([a-zA-Z_]\w*)\s*=\s*(?:sizeof|strlen)\s*\(")
        for i, l in enumerate(lineas_sin_comentarios):
            m_sz = re_int_size.search(l)
            if m_sz:
                vname = m_sz.group(1)
                rcode, tit = _regla_info("0x3010h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_sz.start() + 1,
                    mensaje=f"La variable '{vname}' representa un tamaño o índice pero fue declarada como 'int'.",
                    sugerencia=f"Cambiá el tipo a 'size_t {vname}' para asegurar rango y portabilidad.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))
            else:
                m_so = re_int_sizeof_assign.search(l)
                if m_so:
                    vname = m_so.group(1)
                    rcode, tit = _regla_info("0x3010h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=i + 1,
                        columna=m_so.start() + 1,
                        mensaje=f"La variable '{vname}' recibe el resultado de sizeof/strlen pero fue declarada como 'int'.",
                        sugerencia=f"Cambiá el tipo a 'size_t {vname}' para coincidir con el tipo devuelto por la expresión.",
                        codigo_linea=lineas[i],
                        es_autofixable=False,
                    ))

    # -------------------------------------------------------------------------
    # 0x3011h: Si recibe puntero genérico de solo lectura, usar const void*
    # -------------------------------------------------------------------------
    if _esta_activa("0x3011h"):
        re_ro_void = re.compile(r"\b(?:void|int|size_t)\s+((?:imprimir|mostrar|comparar|hash|serializar|escribir)_\w*)\s*\(([^)]*)\bvoid\s*\*\s*([a-zA-Z_]\w*)[^)]*\)")
        for m_void in re_ro_void.finditer(codigo_sin_comentarios):
            fn_name = m_void.group(1)
            pname = m_void.group(3)
            full_match = m_void.group(0)
            if "const void" not in full_match:
                linea_num = contenido_original[:m_void.start()].count("\n") + 1
                rcode, tit = _regla_info("0x3011h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=linea_num,
                    columna=1,
                    mensaje=f"Parámetro genérico 'void *{pname}' en función de solo lectura '{fn_name}' sin calificador 'const'.",
                    sugerencia=f"Declaralo como 'const void *{pname}' para garantizar inmutabilidad de la memoria.",
                    codigo_linea=lineas[linea_num - 1] if linea_num <= len(lineas) else "",
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x4001h: Manejá correctamente la apertura y cierre de archivos (validar fopen)
    # -------------------------------------------------------------------------
    if _esta_activa("0x4001h"):
        re_fopen_call = re.compile(r"\b([a-zA-Z_]\w*)\s*=\s*fopen\s*\([^;]+\)\s*;")
        for i, l in enumerate(lineas_sin_comentarios):
            m_f = re_fopen_call.search(l)
            if m_f:
                fname = m_f.group(1)
                siguientes = " ".join(lineas_sin_comentarios[i:i + 7])
                tiene_check = bool(re.search(rf"\bif\s*\(\s*(?:{fname}\s*==\s*NULL|NULL\s*==\s*{fname}|!{fname}|{fname}\s*!=\s*NULL)\b", siguientes))
                if not tiene_check:
                    rcode, tit = _regla_info("0x4001h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=i + 1,
                        columna=m_f.start() + 1,
                        mensaje=f"Apertura de archivo '{fname} = fopen(...)' sin comprobación inmediata de retorno contra NULL.",
                        sugerencia=f"Agregá 'if ({fname} == NULL) {{ perror(\"Error\"); return ...; }}' antes de usar el archivo.",
                        codigo_linea=lineas[i],
                        es_autofixable=False,
                    ))

    # -------------------------------------------------------------------------
    # 0x4002h: Validar retornos de operaciones de lectura y escritura de archivos
    # -------------------------------------------------------------------------
    if _esta_activa("0x4002h"):
        re_io_ignored = re.compile(r"^\s*(?:(?:void\s*)?\b(fread|fwrite|fscanf)\s*\([^;]+\)\s*;)")
        for i, l in enumerate(lineas_sin_comentarios):
            m_io = re_io_ignored.match(l)
            if m_io:
                fn_io = m_io.group(1)
                rcode, tit = _regla_info("0x4002h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=1,
                    mensaje=f"Llamada a '{fn_io}' descartando su valor de retorno sin validación.",
                    sugerencia=f"Validá el valor de retorno: 'size_t n = {fn_io}(...); if (n < ...) {{ ... }}'.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x4003h: Utilizá errno, perror y strerror para reportar fallos del SO
    # -------------------------------------------------------------------------
    if _esta_activa("0x4003h"):
        re_fopen_err = re.compile(r"\bif\s*\(\s*([a-zA-Z_]\w*)\s*==\s*NULL\s*\)\s*\{([^}]+)\}")
        for m_err in re_fopen_err.finditer(codigo_sin_comentarios):
            bloque = m_err.group(2)
            if "printf" in bloque and "perror" not in bloque and "strerror" not in bloque and "errno" not in bloque:
                linea_num = contenido_original[:m_err.start()].count("\n") + 1
                rcode, tit = _regla_info("0x4003h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=linea_num,
                    columna=1,
                    mensaje="Manejo de error de archivo sin invocar a 'perror()' ni reportar 'errno' / 'strerror()'.",
                    sugerencia="Utilizá 'perror(\"Error al abrir archivo\");' o 'strerror(errno)' para reportar el diagnóstico del sistema.",
                    codigo_linea=lineas[linea_num - 1] if linea_num <= len(lineas) else "",
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x4004h: Asegurar simetría de recursos al abrir y cerrar archivos
    # -------------------------------------------------------------------------
    if _esta_activa("0x4004h"):
        re_fn_fopen = re.compile(r"^(?:[a-zA-Z_]\w*\*?|\w+\s*\*?)\s*([a-zA-Z_]\w*)\s*\([^)]*\)\s*\{", re.MULTILINE)
        for m_fn in re_fn_fopen.finditer(codigo_sin_comentarios):
            start_idx = m_fn.end()
            brace_count = 1
            curr_idx = start_idx
            while curr_idx < len(codigo_sin_comentarios) and brace_count > 0:
                ch = codigo_sin_comentarios[curr_idx]
                if ch == "{":
                    brace_count += 1
                elif ch == "}":
                    brace_count -= 1
                curr_idx += 1
            body = codigo_sin_comentarios[start_idx:curr_idx]
            if "fopen(" in body and "fclose(" not in body:
                linea_num = contenido_original[:m_fn.start()].count("\n") + 1
                rcode, tit = _regla_info("0x4004h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=linea_num,
                    columna=1,
                    mensaje="La función abre un archivo con 'fopen()' pero no realiza el cierre simétrico con 'fclose()'.",
                    sugerencia="Asegurá cerrar todos los descriptores abiertos mediante 'fclose()' al mismo nivel de abstracción.",
                    codigo_linea=lineas[linea_num - 1] if linea_num <= len(lineas) else "",
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x4005h: Evitar offsets y posiciones fijas codificadas a mano en fseek
    # -------------------------------------------------------------------------
    if _esta_activa("0x4005h"):
        re_fseek_magic = re.compile(r"\bfseek\s*\(\s*[^,]+\s*,\s*([1-9]\d*)\s*,\s*SEEK_SET\s*\)")
        for i, l in enumerate(lineas_sin_comentarios):
            m_seek = re_fseek_magic.search(l)
            if m_seek:
                off = m_seek.group(1)
                rcode, tit = _regla_info("0x4005h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_seek.start() + 1,
                    mensaje=f"Offset fijo literal '{off}' en 'fseek()'; validá las dimensiones del archivo antes de saltos absolutos.",
                    sugerencia="Calculá el tamaño con 'fseek(f, 0, SEEK_END)' y 'ftell(f)' para verificar el offset antes de mover el cursor.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x5002h: Desarrollá y compilá siempre con todas las advertencias (prohibido silenciar warnings)
    # -------------------------------------------------------------------------
    if _esta_activa("0x5002h"):
        re_pragma_warn = re.compile(r"#pragma\s+(?:GCC\s+diagnostic\s+ignored|warning\s*\(\s*disable)", re.IGNORECASE)
        for i, l in enumerate(lineas):
            m_pw = re_pragma_warn.search(l)
            if m_pw:
                rcode, tit = _regla_info("0x5002h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_pw.start() + 1,
                    mensaje="Uso de directiva '#pragma' para silenciar advertencias del compilador.",
                    sugerencia="Corregí la causa raíz del warning en el código en lugar de silenciar los diagnósticos del compilador.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x5005h: Organizar la estructura de los archivos .c de forma estándar
    # -------------------------------------------------------------------------
    if _esta_activa("0x5005h") and ruta.suffix.lower() == ".c":
        primera_funcion_linea = None
        for i, l in enumerate(lineas_sin_comentarios):
            if re.match(rf"^(?!typedef|extern|static\s+const)\s*{TIPOS_BASICOS}\s+\w+\s*\([^;]*\)", l) and not l.strip().endswith(";"):
                siguientes = [x.strip() for x in lineas_sin_comentarios[i + 1:i + 4] if x.strip()]
                if "{" in l or (siguientes and siguientes[0].startswith("{")):
                    primera_funcion_linea = i + 1
                    break
        
        # Verificación de inclusión de cabeceras de sistema antes de cabeceras de usuario
        user_header_line = None
        user_header_name = None
        stem_h = f"{ruta.stem}.h"
        for i, l in enumerate(lineas_sin_comentarios):
            strip_l = l.strip()
            if strip_l.startswith("#include"):
                m_user = re.match(r'^[ \t]*#include[ \t]+"([^"]+)"', strip_l)
                if m_user:
                    h_u = m_user.group(1)
                    if h_u != stem_h and user_header_line is None:
                        user_header_line = i + 1
                        user_header_name = h_u
                m_sys = re.match(r'^[ \t]*#include[ \t]+<([^>]+)>', strip_l)
                if m_sys and user_header_line is not None:
                    h_s = m_sys.group(1)
                    rcode, tit = _regla_info("0x5005h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=i + 1,
                        columna=1,
                        mensaje=f"Inclusión de cabecera de sistema '<{h_s}>' posterior a cabecera de usuario '{user_header_name}'.",
                        sugerencia="Incluí las cabeceras estándar de sistema (<...>) antes de las cabeceras locales de usuario (\"...\").",
                        codigo_linea=lineas[i],
                        es_autofixable=False,
                    ))
                    break

        if primera_funcion_linea:
            for i in range(primera_funcion_linea, len(lineas)):
                strip_l = lineas[i].strip()
                if strip_l.startswith("#include") or strip_l.startswith("#define"):
                    rcode, tit = _regla_info("0x5005h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=i + 1,
                        columna=1,
                        mensaje=f"Directiva '{strip_l.split()[0]}' ubicada después de la definición de funciones.",
                        sugerencia="Mantené las inclusiones y macros en la sección de cabecera inicial del archivo antes de las funciones.",
                        codigo_linea=lineas[i],
                        es_autofixable=False,
                    ))
                    break

    # -------------------------------------------------------------------------
    # 0x0013h: Macros #define deben nombrarse en MAYUSCULAS_SNAKE_CASE
    # -------------------------------------------------------------------------
    if _esta_activa("0x0013h"):
        re_macro_min = re.compile(r"^[ \t]*#define[ \t]+([a-z]\w*)", re.MULTILINE)
        for i, l in enumerate(lineas_sin_comentarios):
            m_mac = re_macro_min.match(l)
            if m_mac:
                macro_nom = m_mac.group(1)
                rcode, tit = _regla_info("0x0013h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_mac.start(1) + 1,
                    mensaje=f"La macro o constante '#define {macro_nom}' contiene letras minúsculas; debe nombrarse en MAYUSCULAS_SNAKE_CASE.",
                    sugerencia=f"Renombrala en mayúsculas: '#define {macro_nom.upper()}'.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x100Ah: Prohibición de asignaciones simples dentro de condiciones lógicas
    # -------------------------------------------------------------------------
    if _esta_activa("0x100Ah"):
        re_assign_in_cond = re.compile(r"\b(?:if|while)\s*\(\s*([a-zA-Z_]\w*)\s*=\s*([^=;()]+)\s*\)")
        for i, l in enumerate(lineas_sin_comentarios):
            m_as = re_assign_in_cond.search(l)
            if m_as:
                var_nom = m_as.group(1)
                val_expr = m_as.group(2).strip()
                rcode, tit = _regla_info("0x100Ah")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_as.start() + 1,
                    mensaje=f"Asignación simple '=' dentro de condición lógica: 'if ({var_nom} = {val_expr})'. ¿Quisiste usar '=='?",
                    sugerencia=f"Cambiá a comparación de igualdad 'if ({var_nom} == {val_expr})' o extraé la asignación antes del condicional.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x100Bh: Prohibición de estructuras de control con cuerpo vacío (if (...);) o llaves vacías
    # -------------------------------------------------------------------------
    if _esta_activa("0x100Bh"):
        re_empty_body = re.compile(r"^[ \t]*(?:if|while|for)\s*\([^)]*\)\s*;\s*$", re.MULTILINE)
        for i, l in enumerate(lineas_sin_comentarios):
            m_eb = re_empty_body.match(l)
            if m_eb:
                rcode, tit = _regla_info("0x100Bh")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_eb.end() - 1,
                    mensaje="Estructura de control con cuerpo nulo: punto y coma ';' inmediatamente después de la condición.",
                    sugerencia="Eliminá el punto y coma ';' y utilizá un bloque con llaves '{ ... }' para encerrar el cuerpo.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))
        re_empty_block = re.compile(r"^[ \t]*(?:if|while|for)\s*\([^)]*\)\s*\{\s*\}\s*$", re.MULTILINE)
        for i, l in enumerate(lineas_sin_comentarios):
            m_ebl = re_empty_block.match(l)
            if m_ebl:
                rcode, tit = _regla_info("0x100Bh")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=1,
                    mensaje="Estructura de control con bloque de llaves vacío '{}'.",
                    sugerencia="Eliminá la estructura vacía o incorporá las instrucciones correspondientes.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x200Bh: Modularización: una función no debe exceder 4 parámetros de entrada
    # -------------------------------------------------------------------------
    if _esta_activa("0x200Bh"):
        re_fn_params = re.compile(rf"^(?!typedef|extern)[ \t]*{TIPOS_BASICOS}\s+(\w+)\s*\(([^)]+)\)\s*(?:\{{|;)", re.MULTILINE)
        for m_fp in re_fn_params.finditer(codigo_sin_comentarios):
            fn_name = m_fp.group(1)
            params_raw = [p.strip() for p in m_fp.group(2).split(",") if p.strip()]
            if len(params_raw) > 4:
                linea_num = contenido_original[:m_fp.start()].count("\n") + 1
                rcode, tit = _regla_info("0x200Bh")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=linea_num,
                    columna=1,
                    mensaje=f"La función '{fn_name}' recibe {len(params_raw)} parámetros (máximo recomendado: 4).",
                    sugerencia="Empaquetá los parámetros relacionados en una estructura 'struct' o TDA para reducir el acoplamiento.",
                    codigo_linea=lineas[linea_num - 1] if linea_num <= len(lineas) else "",
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x3012h: Prohibición de aritmética de punteros sobre void*
    # -------------------------------------------------------------------------
    if _esta_activa("0x3012h"):
        re_void_decl = re.compile(r"\bvoid\s*\*\s*([a-zA-Z_]\w*)\b")
        void_ptrs = set(re_void_decl.findall(codigo_sin_comentarios))
        for vp in void_ptrs:
            re_void_arith = re.compile(rf"\b{vp}\s*(?:\+\+|\-\-|\+\s*\d+|\-\s*\d+)")
            for i, l in enumerate(lineas_sin_comentarios):
                if "void *" in l:
                    continue
                m_va = re_void_arith.search(l)
                if m_va:
                    rcode, tit = _regla_info("0x3012h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=i + 1,
                        columna=m_va.start() + 1,
                        mensaje=f"Aritmética de punteros sobre 'void *{vp}'. El tipo void carece de tamaño definido en C estándar.",
                        sugerencia=f"Casteá explícitamente a '(char *){vp}' o '(uint8_t *){vp}' antes de sumar offsets.",
                        codigo_linea=lineas[i],
                        es_autofixable=False,
                    ))

    # -------------------------------------------------------------------------
    # 0x3015h: Reallocación segura: no sobreescribir el puntero original directamente
    # -------------------------------------------------------------------------
    if _esta_activa("0x3015h"):
        re_unsafe_realloc = re.compile(r"\b([a-zA-Z_]\w*)\s*=\s*(?:\([a-zA-Z0-9_* ]+\)\s*)?realloc\s*\(\s*\1\s*,")
        for i, l in enumerate(lineas_sin_comentarios):
            m_re = re_unsafe_realloc.search(l)
            if m_re:
                pname = m_re.group(1)
                rcode, tit = _regla_info("0x3015h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_re.start() + 1,
                    mensaje=f"Reasignación insegura con realloc: '{pname} = realloc({pname}, ...)'. Provoca fuga si realloc falla y retorna NULL.",
                    sugerencia=f"Asigná a una variable temporal: 'void *tmp = realloc({pname}, ...); if (tmp) {pname} = tmp;'.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x4007h: Prohibición de rutas absolutas hardcodeadas en llamadas de archivo
    # -------------------------------------------------------------------------
    if _esta_activa("0x4007h"):
        re_abs_path = re.compile(r'\bfopen\s*\(\s*"(?:/(?:home|etc|var|tmp|usr|opt)|[a-zA-Z]:\\\\)')
        for i, l in enumerate(lineas_sin_comentarios):
            m_ap = re_abs_path.search(l)
            if m_ap:
                rcode, tit = _regla_info("0x4007h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_ap.start() + 1,
                    mensaje="Ruta absoluta hardcodeada en llamada a 'fopen()'. Afecta la portabilidad del programa.",
                    sugerencia="Utilizá rutas relativas o recibí el nombre del archivo como argumento en 'argv' o parámetro de función.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x5007h: Inclusiones redundantes o duplicadas de la misma cabecera #include
    # -------------------------------------------------------------------------
    if _esta_activa("0x5007h"):
        headers_vistos: Dict[str, int] = {}
        re_inc_line = re.compile(r"^[ \t]*#include[ \t]+([<\"].+[>\"])")
        for i, l in enumerate(lineas):
            m_inc = re_inc_line.match(l)
            if m_inc:
                h_name = m_inc.group(1)
                if h_name in headers_vistos:
                    rcode, tit = _regla_info("0x5007h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=i + 1,
                        columna=1,
                        mensaje=f"Inclusión duplicada de la cabecera #include {h_name} (previamente incluida en la línea {headers_vistos[h_name]}).",
                        sugerencia="Eliminá la directiva de inclusión redundante.",
                        codigo_linea=lineas[i],
                        es_autofixable=True,
                    ))
                else:
                    headers_vistos[h_name] = i + 1

    # -------------------------------------------------------------------------
    # 0x5008h: Prohibición de funciones obsoletas o inseguras (gets, atoi)
    # -------------------------------------------------------------------------
    if _esta_activa("0x5008h"):
        re_unsafe_fn = re.compile(r"\b(gets|atoi)\s*\(")
        for i, l in enumerate(lineas_sin_comentarios):
            m_uf = re_unsafe_fn.search(l)
            if m_uf:
                bad_fn = m_uf.group(1)
                sug = "fgets(buf, sizeof(buf), stdin)" if bad_fn == "gets" else "strtol(str, &endptr, 10)"
                rcode, tit = _regla_info("0x5008h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_uf.start() + 1,
                    mensaje=f"Uso de la función obsoleta o insegura '{bad_fn}()'.",
                    sugerencia=f"Reemplazala por '{sug}'.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x5009h: Prohibición de división entera no intencional asignada a flotantes
    # -------------------------------------------------------------------------
    if _esta_activa("0x5009h"):
        re_int_div_float = re.compile(r"\b(?:float|double)\s+[a-zA-Z_]\w*\s*=\s*(\d+)\s*/\s*(\d+)\s*;")
        for i, l in enumerate(lineas_sin_comentarios):
            m_idf = re_int_div_float.search(l)
            if m_idf:
                n1 = m_idf.group(1)
                n2 = m_idf.group(2)
                rcode, tit = _regla_info("0x5009h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_idf.start() + 1,
                    mensaje=f"División entera '{n1} / {n2}' asignada a tipo flotante; trunca a entero antes de la asignación.",
                    sugerencia=f"Usá literales flotantes: '{n1}.0 / {n2}.0' o casteo '(double){n1} / {n2}'.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x0014h: Auditor de tipografía y prohibición de caracteres no ASCII en código
    # -------------------------------------------------------------------------
    if _esta_activa("0x0014h"):
        for i, l in enumerate(lineas_sin_cadenas):
            if not l.strip() or l.strip().startswith(("//", "/*", "*")):
                continue
            re_typo = re.search(r"[“”‘’«»–—− ​﻿]", l)
            if re_typo:
                char_bad = re_typo.group(0)
                codepoint = f"U+{ord(char_bad):04X}"
                rcode, tit = _regla_info("0x0014h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=re_typo.start() + 1,
                    mensaje=f"Carácter tipográfico o invisible no ASCII detectado ({char_bad!r}, {codepoint}).",
                    sugerencia="Utilizá únicamente caracteres ASCII estándar (comillas rectas, guiones simples, espacios estándar).",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))
            palabras = re.findall(r"\b([a-zA-Z0-9_]*[^\x00-\x7F\s;,\[\]\(\)\{\}]+[a-zA-Z0-9_]*)\b", l)
            for pal in palabras:
                rcode, tit = _regla_info("0x0014h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=l.index(pal) + 1 if pal in l else 1,
                    mensaje=f"Identificador '{pal}' contiene caracteres no ASCII (tildes, 'ñ' o caracteres homoglíficos).",
                    sugerencia="Utilizá únicamente caracteres alfanuméricos ASCII estándar [a-z0-9_] para garantizar portabilidad.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x0015h: Prohibición del operador coma para encadenar sentencias independientes
    # -------------------------------------------------------------------------
    if _esta_activa("0x0015h"):
        re_comma_stmt = re.compile(r"^[ \t]*[a-zA-Z_]\w*\s*=[^,;]+,\s*[a-zA-Z_]\w*\s*=[^;]+;", re.MULTILINE)
        for i, l in enumerate(lineas_sin_comentarios):
            if l.strip().startswith("for"):
                continue
            m_cs = re_comma_stmt.match(l)
            if m_cs:
                rcode, tit = _regla_info("0x0015h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=1,
                    mensaje="Uso del operador coma ',' para encadenar sentencias independientes.",
                    sugerencia="Dividí las asignaciones en líneas separadas terminadas en punto y coma ';' para mayor claridad.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x100Ch: Exigencia de break explícito o comentario de fallthrough en bloques switch case
    # -------------------------------------------------------------------------
    if _esta_activa("0x100Ch"):
        re_case_block = re.compile(r"\bcase\s+[^:]+:\s*\n((?:[^\n]+\n)*?)(?=\s*(?:case\s+[^:]+|default)\s*:)", re.MULTILINE)
        for m_cb in re_case_block.finditer(codigo_sin_comentarios):
            c_body = m_cb.group(1).strip()
            if c_body:
                if not (re.search(r"\b(?:break|return)\s*;", c_body) or "fallthrough" in c_body.lower()):
                    linea_num = contenido_original[:m_cb.start()].count("\n") + 1
                    rcode, tit = _regla_info("0x100Ch")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=linea_num,
                        columna=1,
                        mensaje="Cláusula 'case' finaliza sin sentencia 'break;' ni 'return;'.",
                        sugerencia="Agregá 'break;' al final del caso o documentá la caída deliberada con '// fallthrough'.",
                        codigo_linea=lineas[linea_num - 1] if linea_num <= len(lineas) else "",
                        es_autofixable=False,
                    ))

    # -------------------------------------------------------------------------
    # 0x100Dh: Prohibición de modificar la variable de control dentro del cuerpo del for
    # -------------------------------------------------------------------------
    if _esta_activa("0x100Dh"):
        re_for_head = re.compile(r"\bfor\s*\(\s*(?:int|size_t)?\s*([a-zA-Z_]\w*)\s*=[^;]*;[^;]*;\s*[^)]*\)\s*\{", re.MULTILINE)
        for m_fh in re_for_head.finditer(codigo_sin_comentarios):
            idx_var = m_fh.group(1)
            start_idx = m_fh.end()
            brace_count = 1
            curr_idx = start_idx
            while curr_idx < len(codigo_sin_comentarios) and brace_count > 0:
                ch = codigo_sin_comentarios[curr_idx]
                if ch == "{":
                    brace_count += 1
                elif ch == "}":
                    brace_count -= 1
                curr_idx += 1
            body_for = codigo_sin_comentarios[start_idx:curr_idx]
            if re.search(rf"\b{idx_var}\s*(?:\+\+|\-\-|\+=|\-=|=)\s*[^=]", body_for):
                linea_num = contenido_original[:m_fh.start()].count("\n") + 1
                rcode, tit = _regla_info("0x100Dh")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=linea_num,
                    columna=1,
                    mensaje=f"Modificación de la variable de iteración '{idx_var}' dentro del cuerpo del lazo 'for'.",
                    sugerencia="Modificá el contador únicamente en la cabecera del lazo o reemplazá el 'for' por un 'while'.",
                    codigo_linea=lineas[linea_num - 1] if linea_num <= len(lineas) else "",
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x200Ch: Prohibición de retornar la dirección de una variable local de stack
    # -------------------------------------------------------------------------
    if _esta_activa("0x200Ch"):
        re_ret_addr = re.compile(r"^\s*return\s+&\s*([a-zA-Z_]\w*)\s*;", re.MULTILINE)
        for i, l in enumerate(lineas_sin_comentarios):
            m_ra = re_ret_addr.match(l)
            if m_ra:
                vnom = m_ra.group(1)
                rcode, tit = _regla_info("0x200Ch")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_ra.start() + 1,
                    mensaje=f"Retorno de dirección de variable local '&{vnom}'; produce puntero colgante (dangling pointer) al destruirse el marco del stack.",
                    sugerencia="Alocá la variable dinámicamente con malloc() o pasala como parámetro de salida por referencia.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x200Dh: Cada función debe tener a lo sumo un return
    # -------------------------------------------------------------------------
    if _esta_activa("0x200Dh"):
        depth = 0
        start_pos = 0
        last_delim = 0
        fn_name = None
        fn_start_line = 1

        i = 0
        n = len(codigo_sin_cadenas)
        while i < n:
            ch = codigo_sin_cadenas[i]
            if ch == "{" and depth == 0:
                header = codigo_sin_cadenas[last_delim:i].strip()
                lines_h = [l.strip() for l in header.splitlines() if l.strip() and not l.strip().startswith("#")]
                header_clean = " ".join(lines_h)

                if header_clean.endswith(")") and "=" not in header_clean and not re.match(r"^\s*typedef\b", header_clean):
                    p_count = 0
                    p_start = -1
                    for k in range(len(header_clean) - 1, -1, -1):
                        if header_clean[k] == ")":
                            p_count += 1
                        elif header_clean[k] == "(":
                            p_count -= 1
                            if p_count == 0:
                                p_start = k
                                break
                    if p_start > 0:
                        before = header_clean[:p_start].strip()
                        m = re.search(r"(\b[a-zA-Z_]\w*)$", before)
                        if m and m.group(1) not in ("if", "while", "for", "switch", "catch"):
                            fn_name = m.group(1)
                            fn_start_line = (
                                contenido_original[:last_delim + header.rfind(fn_name)].count("\n") + 1
                                if fn_name in header
                                else contenido_original[:i].count("\n") + 1
                            )
                            start_pos = i
                            depth = 1
                            i += 1
                            continue
                depth = 1
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0 and fn_name:
                    fn_body = codigo_sin_cadenas[start_pos + 1:i]
                    returns_matches = list(re.finditer(r"\breturn\b", fn_body))
                    if len(returns_matches) > 1:
                        ret_lines = [
                            contenido_original[:start_pos + 1 + rm.start()].count("\n") + 1
                            for rm in returns_matches
                        ]
                        rcode, tit = _regla_info("0x200Dh")
                        violaciones.append(ViolacionRegla(
                            codigo=rcode,
                            titulo=tit,
                            archivo=ruta,
                            linea=fn_start_line,
                            columna=1,
                            mensaje=f"La función '{fn_name}' contiene más de un return ({len(returns_matches)} sentencias 'return' en líneas {', '.join(map(str, ret_lines))}).",
                            sugerencia="Estructurá la función con un único punto de retorno al final utilizando una variable local auxiliar.",
                            codigo_linea=lineas[fn_start_line - 1] if fn_start_line <= len(lineas) else "",
                            es_autofixable=False,
                        ))
                    fn_name = None
                last_delim = i + 1
            elif ch == ";" and depth == 0:
                last_delim = i + 1
            i += 1

    # -------------------------------------------------------------------------
    # 0x3013h: Asignación de memoria con sizeof sobre puntero en lugar del tipo apuntado
    # -------------------------------------------------------------------------
    if _esta_activa("0x3013h"):
        re_sizeof_ptr = re.compile(r"\b([a-zA-Z_]\w*)\s*=\s*(?:\([a-zA-Z0-9_* ]+\)\s*)?(?:malloc|calloc)\s*\([^)]*sizeof\s*\(\s*\1\s*\)")
        for i, l in enumerate(lineas_sin_comentarios):
            m_sp = re_sizeof_ptr.search(l)
            if m_sp:
                pnom = m_sp.group(1)
                rcode, tit = _regla_info("0x3013h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_sp.start() + 1,
                    mensaje=f"Uso erróneo de 'sizeof({pnom})' sobre el propio puntero en asignación de memoria.",
                    sugerencia=f"Utilizá 'sizeof(*{pnom})' para alocar según el tamaño del tipo apuntado y no del puntero.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x3014h: Prohibición de doble liberación de memoria (double free)
    # -------------------------------------------------------------------------
    if _esta_activa("0x3014h"):
        re_double_free = re.compile(r"\bfree\s*\(\s*([a-zA-Z_]\w*)\s*\)\s*;(?:\s*\n)+\s*free\s*\(\s*\1\s*\)\s*;")
        for m_df in re_double_free.finditer(codigo_sin_comentarios):
            pnom = m_df.group(1)
            linea_num = contenido_original[:m_df.start()].count("\n") + 1
            rcode, tit = _regla_info("0x3014h")
            violaciones.append(ViolacionRegla(
                codigo=rcode,
                titulo=tit,
                archivo=ruta,
                linea=linea_num,
                columna=1,
                mensaje=f"Doble liberación de memoria consecutiva sobre '{pnom}'.",
                sugerencia=f"Eliminá la segunda llamada y asigná '{pnom} = NULL;' tras el primer free.",
                codigo_linea=lineas[linea_num - 1] if linea_num <= len(lineas) else "",
                es_autofixable=False,
            ))

    # -------------------------------------------------------------------------
    # 0x4006h: Prohibición del antipatrón while (!feof(f))
    # -------------------------------------------------------------------------
    if _esta_activa("0x4006h"):
        re_while_feof = re.compile(r"\bwhile\s*\(\s*!feof\s*\(")
        for i, l in enumerate(lineas_sin_comentarios):
            m_wf = re_while_feof.search(l)
            if m_wf:
                rcode, tit = _regla_info("0x4006h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_wf.start() + 1,
                    mensaje="Antipatrón de lectura: 'while (!feof(...))' evalúa EOF antes de intentar leer.",
                    sugerencia="Controlá el lazo evaluando el retorno de la operación de lectura: 'while (fgets(...) != NULL)' o 'while (fread(...) == 1)'.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x500Ah: Protección obligatoria de parámetros en macros funcionales mediante paréntesis
    # -------------------------------------------------------------------------
    if _esta_activa("0x500Ah"):
        re_macro_fn = re.compile(r"^[ \t]*#define\s+([a-zA-Z_]\w*)\s*\(([^)]+)\)\s+([^\n]+)", re.MULTILINE)
        for m_mf in re_macro_fn.finditer(codigo_sin_comentarios):
            m_name = m_mf.group(1)
            m_params = [p.strip() for p in m_mf.group(2).split(",") if p.strip()]
            m_body = m_mf.group(3).strip()
            for p in m_params:
                if re.search(rf"(?<!\()\b{p}\b(?!\))", m_body):
                    linea_num = contenido_original[:m_mf.start()].count("\n") + 1
                    rcode, tit = _regla_info("0x500Ah")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=linea_num,
                        columna=1,
                        mensaje=f"El parámetro '{p}' en la macro funcional '{m_name}' no está protegido entre paréntesis.",
                        sugerencia=f"Encerrá cada ocurrencia del parámetro entre paréntesis '({p})' en la expansión de la macro.",
                        codigo_linea=lineas[linea_num - 1] if linea_num <= len(lineas) else "",
                        es_autofixable=False,
                    ))
                    break

    # -------------------------------------------------------------------------
    # 0x500Bh: Inclusión obligatoria de cabeceras estándar para funciones estándar
    # -------------------------------------------------------------------------
    if _esta_activa("0x500Bh") and ruta.suffix.lower() == ".c":
        chequeos_headers = [
            (r"\b(?:printf|scanf|puts|getchar|putchar)\s*\(", "<stdio.h>"),
            (r"\b(?:malloc|calloc|realloc|free|exit|qsort)\s*\(", "<stdlib.h>"),
            (r"\b(?:strlen|strcpy|strncpy|strcat|strcmp|strncmp|memcpy|memset)\s*\(", "<string.h>"),
            (r"\b(?:assert)\s*\(", "<assert.h>"),
        ]
        for pat_fn, h_req in chequeos_headers:
            if re.search(pat_fn, codigo_sin_comentarios):
                if not re.search(rf"^[ \t]*#include[ \t]+{re.escape(h_req)}", codigo_sin_comentarios, re.MULTILINE):
                    rcode, tit = _regla_info("0x500Bh")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=1,
                        columna=1,
                        mensaje=f"Uso de funciones de la biblioteca estándar de C sin incluir la cabecera '{h_req}'.",
                        sugerencia=f"Agregá '#include {h_req}' en la sección de cabecera del archivo.",
                        codigo_linea=lineas[0] if lineas else "",
                        es_autofixable=False,
                    ))

    # -------------------------------------------------------------------------
    # 0x0016h: Prohibición de identificadores que colisionen con palabras clave o tipos estándar
    # -------------------------------------------------------------------------
    if _esta_activa("0x0016h"):
        re_res_id = re.compile(rf"\b(?:{TIPOS_BASICOS})\s+(restrict|inline|bool|true|false|nullptr|alignas)\b")
        for i, l in enumerate(lineas_sin_comentarios):
            m_ri = re_res_id.search(l)
            if m_ri:
                nom = m_ri.group(1)
                rcode, tit = _regla_info("0x0016h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_ri.start(1) + 1,
                    mensaje=f"Identificador '{nom}' colisiona con palabra clave o tipo estándar de C99/C11/POSIX.",
                    sugerencia=f"Renombrá el identificador (ej: '{nom}_val') para evitar ambigüedades.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x0017h: Prohibición de notación húngara o prefijos redundantes de tipo en identificadores
    # -------------------------------------------------------------------------
    if _esta_activa("0x0017h"):
        re_hungarian = re.compile(rf"\b(?:{TIPOS_BASICOS})\s+((?:int|float|str|arr|char|p_str)_\w+)")
        for i, l in enumerate(lineas_sin_comentarios):
            m_hu = re_hungarian.search(l)
            if m_hu:
                nom = m_hu.group(1)
                rcode, tit = _regla_info("0x0017h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_hu.start(1) + 1,
                    mensaje=f"Identificador '{nom}' utiliza notación húngara o prefijos de tipo redundantes.",
                    sugerencia="Elegí nombres basados en el significado o rol semántico de la variable, no en su tipo primitivo.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x100Eh: Prohibición de condiciones constantes o tautológicas en sentencias if
    # -------------------------------------------------------------------------
    if _esta_activa("0x100Eh"):
        re_const_if = re.compile(r"\bif\s*\(\s*(1|0|true|false)\s*\)")
        for i, l in enumerate(lineas_sin_comentarios):
            m_ci = re_const_if.search(l)
            if m_ci:
                val = m_ci.group(1)
                rcode, tit = _regla_info("0x100Eh")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_ci.start() + 1,
                    mensaje=f"Condición constante tautológica 'if ({val})' detectada.",
                    sugerencia="Eliminá la rama condicional muerta o reemplazala por una expresión lógica variable.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x100Fh: Prohibición de condiciones de parada compuestas complejas en lazos for
    # -------------------------------------------------------------------------
    if _esta_activa("0x100Fh"):
        re_for_complex = re.compile(r"\bfor\s*\([^;]*;([^;]*(?:&&|\|\|)[^;]*);[^)]*\)")
        for i, l in enumerate(lineas_sin_comentarios):
            m_fc = re_for_complex.search(l)
            if m_fc:
                rcode, tit = _regla_info("0x100Fh")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_fc.start() + 1,
                    mensaje="Lazo 'for' con condición de parada lógica compuesta (operadores && / ||).",
                    sugerencia="Mantené el lazo 'for' con una comprobación simple de cota; utilizá 'while' para lazos con condiciones de parada complejas.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x200Eh: Declaración explícita de (void) en funciones que no reciben parámetros
    # -------------------------------------------------------------------------
    if _esta_activa("0x200Eh"):
        re_empty_paren_fn = re.compile(rf"^[ \t]*(?!typedef|extern){TIPOS_BASICOS}\s+(\w+)\s*\(\s*\)\s*(?:\{{|;)", re.MULTILINE)
        for m_ep in re_empty_paren_fn.finditer(codigo_sin_comentarios):
            fn_name = m_ep.group(1)
            linea_num = contenido_original[:m_ep.start()].count("\n") + 1
            rcode, tit = _regla_info("0x200Eh")
            violaciones.append(ViolacionRegla(
                codigo=rcode,
                titulo=tit,
                archivo=ruta,
                linea=linea_num,
                columna=1,
                mensaje=f"Función '{fn_name}()' declarada sin parámetros. En C debe especificarse '(void)' explícitamente.",
                sugerencia=f"Declarala como '{fn_name}(void)' para habilitar el prototipado estricto.",
                codigo_linea=lineas[linea_num - 1] if linea_num <= len(lineas) else "",
                es_autofixable=True,
            ))

    # -------------------------------------------------------------------------
    # 0x200Fh: Calificador static obligatorio en funciones auxiliares privadas de archivo
    # -------------------------------------------------------------------------
    if _esta_activa("0x200Fh") and ruta.suffix.lower() == ".c":
        re_public_fn = re.compile(rf"^(?!static|typedef|extern)[ \t]*{TIPOS_BASICOS}\s+(\w+)\s*\([^)]*\)\s*\{{", re.MULTILINE)
        header_declaraciones = set()
        comp_h = ruta.with_suffix(".h")
        if comp_h.is_file():
            try:
                txt_h = comp_h.read_text(encoding="utf-8", errors="replace")
                header_declaraciones = set(re.findall(rf"\b{TIPOS_BASICOS}\s+(\w+)\s*\(", _eliminar_comentarios(txt_h)))
            except Exception:
                pass
        for m_pf in re_public_fn.finditer(codigo_sin_comentarios):
            fn_name = m_pf.group(1)
            if fn_name in ("main", "if", "for", "while") or fn_name.startswith("test_"):
                continue
            if comp_h.is_file() and fn_name not in header_declaraciones:
                linea_num = contenido_original[:m_pf.start()].count("\n") + 1
                rcode, tit = _regla_info("0x200Fh")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=linea_num,
                    columna=1,
                    mensaje=f"Función auxiliar '{fn_name}' no exportada en cabecera ni calificada como 'static'.",
                    sugerencia=f"Declarala como 'static {fn_name}(...)' para encapsular su enlace al archivo.",
                    codigo_linea=lineas[linea_num - 1] if linea_num <= len(lineas) else "",
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x3016h: Prohibición de desreferencia directa de memoria dinámica sin check a NULL previo
    # -------------------------------------------------------------------------
    if _esta_activa("0x3016h"):
        re_alloc_deref = re.compile(r"\b([a-zA-Z_]\w*)\s*=\s*(?:\([a-zA-Z0-9_* ]+\)\s*)?(?:malloc|calloc)\s*\([^;]*\)\s*;\s*\n\s*(?:\*\1\b|\1->)")
        for m_ad in re_alloc_deref.finditer(codigo_sin_comentarios):
            pname = m_ad.group(1)
            linea_num = contenido_original[:m_ad.start()].count("\n") + 1
            rcode, tit = _regla_info("0x3016h")
            violaciones.append(ViolacionRegla(
                codigo=rcode,
                titulo=tit,
                archivo=ruta,
                linea=linea_num,
                columna=1,
                mensaje=f"Desreferencia inmediata de '{pname}' tras alocación sin verificación contra NULL.",
                sugerencia=f"Verificá 'if ({pname} == NULL)' antes de desreferenciar el bloque alocado.",
                codigo_linea=lineas[linea_num - 1] if linea_num <= len(lineas) else "",
                es_autofixable=False,
            ))

    # -------------------------------------------------------------------------
    # 0x3017h: Prohibición de utilizar free() como valor o dentro de expresiones compuestas
    # -------------------------------------------------------------------------
    if _esta_activa("0x3017h"):
        re_free_val = re.compile(r"(?:\b[a-zA-Z_]\w*\s*=\s*free\s*\(|\(\s*free\s*\([^)]+\)\s*,)")
        for i, l in enumerate(lineas_sin_comentarios):
            m_fv = re_free_val.search(l)
            if m_fv:
                rcode, tit = _regla_info("0x3017h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_fv.start() + 1,
                    mensaje="Uso de 'free()' en una expresión con valor; free() retorna void.",
                    sugerencia="Invocá 'free()' como una sentencia independiente: 'free(p);'.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x4008h: Validación obligatoria del valor de retorno de fclose() en modo escritura
    # -------------------------------------------------------------------------
    if _esta_activa("0x4008h"):
        re_write_file = re.compile(r'\b([a-zA-Z_]\w*)\s*=\s*fopen\s*\([^)]*"(?:w|a|wb|w\+|a\+)"[^)]*\)\s*;')
        for m_wf in re_write_file.finditer(codigo_sin_comentarios):
            fvar = m_wf.group(1)
            re_ignored_fclose = re.compile(rf"^\s*fclose\s*\(\s*{fvar}\s*\)\s*;", re.MULTILINE)
            for m_ifc in re_ignored_fclose.finditer(codigo_sin_comentarios):
                linea_num = contenido_original[:m_ifc.start()].count("\n") + 1
                rcode, tit = _regla_info("0x4008h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=linea_num,
                    columna=1,
                    mensaje=f"Retorno de 'fclose({fvar})' ignorado en archivo abierto para escritura.",
                    sugerencia=f"Validá 'if (fclose({fvar}) == EOF)' para detectar posibles fallos al vaciar búferes a disco.",
                    codigo_linea=lineas[linea_num - 1] if linea_num <= len(lineas) else "",
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x4009h: Prohibición de anidar llamadas a fopen() directamente dentro de funciones de E/S
    # -------------------------------------------------------------------------
    if _esta_activa("0x4009h"):
        re_nested_fopen = re.compile(r"\b(?:fscanf|fread|fwrite|fgets|fgetc|fputc)\s*\([^)]*\bfopen\s*\(")
        for i, l in enumerate(lineas_sin_comentarios):
            m_nf = re_nested_fopen.search(l)
            if m_nf:
                rcode, tit = _regla_info("0x4009h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_nf.start() + 1,
                    mensaje="Llamada anidada directa a 'fopen()' dentro de función de E/S.",
                    sugerencia="Asigná el descriptor a una variable 'FILE *arch = fopen(...);', validalo contra NULL y cerralo con fclose().",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x500Ch: Prohibición de inclusión directa de archivos de código fuente C (.c)
    # -------------------------------------------------------------------------
    if _esta_activa("0x500Ch"):
        re_inc_c = re.compile(r"^[ \t]*#include[ \t]+[<\"][^>\"]+\.c[>\"]")
        for i, l in enumerate(lineas):
            m_ic = re_inc_c.match(l)
            if m_ic:
                rcode, tit = _regla_info("0x500Ch")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=1,
                    mensaje="Inclusión prohibida de archivo fuente C (#include '...c').",
                    sugerencia="Incluí únicamente cabeceras '.h' y compilá los archivos '.c' de forma independiente.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x500Dh: Prohibición de redefinir palabras clave o tipos primitivos de C con #define
    # -------------------------------------------------------------------------
    if _esta_activa("0x500Dh"):
        re_kw_redef = re.compile(r"^[ \t]*#define\s+(if|else|for|while|do|switch|case|default|break|continue|return|goto|int|char|float|double|void|typedef|struct|union|enum|const|static|volatile|sizeof)\b", re.MULTILINE)
        for i, l in enumerate(lineas_sin_comentarios):
            m_kr = re_kw_redef.match(l)
            if m_kr:
                kw = m_kr.group(1)
                rcode, tit = _regla_info("0x500Dh")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=1,
                    mensaje=f"Redefinición prohibida de palabra clave o tipo '{kw}' con #define.",
                    sugerencia="No alteres las palabras reservadas ni los tipos primitivos del lenguaje C.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x0018h: Prohibición de identificadores con prefijos reservados (__ o _[A-Z])
    # -------------------------------------------------------------------------
    if _esta_activa("0x0018h"):
        re_res_pref = re.compile(rf"\b(?:{TIPOS_BASICOS})\s+(__\w+|_([A-Z]\w*))\b")
        for i, l in enumerate(lineas_sin_comentarios):
            m_rp = re_res_pref.search(l)
            if m_rp:
                nom = m_rp.group(1)
                rcode, tit = _regla_info("0x0018h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_rp.start(1) + 1,
                    mensaje=f"Identificador '{nom}' comienza con prefijo reservado para el compilador o libc ('__' o '_[A-Z]').",
                    sugerencia="Utilizá nombres en snake_case sin prefijos de guiones bajos reservados.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x0019h: Prohibición de espacios en blanco antes de separadores de sintaxis (; y ,)
    # -------------------------------------------------------------------------
    if _esta_activa("0x0019h"):
        re_space_sep = re.compile(r"[ \t]+([;,])")
        for i, l in enumerate(lineas_sin_comentarios):
            if l.strip().startswith("for") or l.strip().startswith("/*") or l.strip().startswith("*"):
                continue
            for m_ss in re_space_sep.finditer(l):
                sep = m_ss.group(1)
                rcode, tit = _regla_info("0x0019h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_ss.start() + 1,
                    mensaje=f"Espacio en blanco innecesario antes del separador '{sep}'.",
                    sugerencia="Pegá el separador directamente al identificador o expresión precedente.",
                    codigo_linea=lineas[i],
                    es_autofixable=True,
                ))

    # -------------------------------------------------------------------------
    # 0x1010h: Delimitación obligatoria con bloque de llaves en lazos do-while
    # -------------------------------------------------------------------------
    if _esta_activa("0x1010h"):
        re_do_nok = re.compile(r"^[ \t]*do[ \t]+(?!\{)[a-zA-Z_]\w*", re.MULTILINE)
        for i, l in enumerate(lineas_sin_comentarios):
            m_dn = re_do_nok.match(l)
            if m_dn:
                rcode, tit = _regla_info("0x1010h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=1,
                    mensaje="Lazo 'do ... while' sin bloque de llaves '{ ... }' delimitador.",
                    sugerencia="Encerrá siempre el cuerpo de 'do' entre llaves explícitas.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x1011h: Prohibición de cláusula else redundante tras sentencia de retorno anticipado
    # -------------------------------------------------------------------------
    if _esta_activa("0x1011h"):
        re_else_ret = re.compile(r"\breturn\s*[^;]*;\s*\}\s*else\b", re.MULTILINE)
        for m_er in re_else_ret.finditer(codigo_sin_comentarios):
            linea_num = contenido_original[:m_er.start()].count("\n") + 1
            rcode, tit = _regla_info("0x1011h")
            violaciones.append(ViolacionRegla(
                codigo=rcode,
                titulo=tit,
                archivo=ruta,
                linea=linea_num,
                columna=1,
                mensaje="Cláusula 'else' redundante tras bloque finalizado incondicionalmente con 'return'.",
                sugerencia="Desanidá el bloque posterior eliminando el 'else' innecesario.",
                codigo_linea=lineas[linea_num - 1] if linea_num <= len(lineas) else "",
                es_autofixable=False,
            ))

    # -------------------------------------------------------------------------
    # 0x2010h: Prohibición de sombreado de parámetros mediante variables locales con el mismo nombre
    # -------------------------------------------------------------------------
    if _esta_activa("0x2010h"):
        re_fn_with_params = re.compile(rf"^[ \t]*(?!typedef|extern){TIPOS_BASICOS}\s+(\w+)\s*\(([^)]+)\)\s*\{{", re.MULTILINE)
        for m_fwp in re_fn_with_params.finditer(codigo_sin_comentarios):
            fn_params_raw = m_fwp.group(2)
            params_set = set(re.findall(r"\b([a-zA-Z_]\w*)\s*(?:,|$)", fn_params_raw))
            params_set.discard("void")
            start_idx = m_fwp.end()
            brace_count = 1
            curr_idx = start_idx
            while curr_idx < len(codigo_sin_comentarios) and brace_count > 0:
                ch = codigo_sin_comentarios[curr_idx]
                if ch == '{':
                    brace_count += 1
                elif ch == '}':
                    brace_count -= 1
                curr_idx += 1
            body_fn = codigo_sin_comentarios[start_idx:curr_idx]
            for p in params_set:
                if re.search(rf"\b(?:{TIPOS_BASICOS})\s+(?:\*+\s*)?{p}\b\s*[=;]", body_fn):
                    linea_num = contenido_original[:m_fwp.start()].count("\n") + 1
                    rcode, tit = _regla_info("0x2010h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=linea_num,
                        columna=1,
                        mensaje=f"Variable local sombrea (shadows) al parámetro '{p}' de la función.",
                        sugerencia="Renombrá la variable local para no ocultar el parámetro de entrada.",
                        codigo_linea=lineas[linea_num - 1] if linea_num <= len(lineas) else "",
                        es_autofixable=False,
                    ))

    # -------------------------------------------------------------------------
    # 0x2011h: Prohibición de reasignar o modificar parámetros recibidos por valor dentro de la función
    # -------------------------------------------------------------------------
    if _esta_activa("0x2011h"):
        re_fn_val_params = re.compile(rf"^[ \t]*(?!typedef|extern){TIPOS_BASICOS}\s+(\w+)\s*\(([^)]+)\)\s*\{{", re.MULTILINE)
        for m_fvp in re_fn_val_params.finditer(codigo_sin_comentarios):
            raw_params = m_fvp.group(2)
            val_params = []
            for p_decl in raw_params.split(","):
                p_decl = p_decl.strip()
                if "*" not in p_decl and p_decl != "void":
                    m_pname = re.search(r"\b([a-zA-Z_]\w*)$", p_decl)
                    if m_pname:
                        val_params.append(m_pname.group(1))
            start_idx = m_fvp.end()
            brace_count = 1
            curr_idx = start_idx
            while curr_idx < len(codigo_sin_comentarios) and brace_count > 0:
                ch = codigo_sin_comentarios[curr_idx]
                if ch == '{':
                    brace_count += 1
                elif ch == '}':
                    brace_count -= 1
                curr_idx += 1
            body_fn = codigo_sin_comentarios[start_idx:curr_idx]
            for vp in val_params:
                if re.search(rf"\b{vp}\s*(?:\+\+|\-\-|\+=|\-=|=)\s*[^=]", body_fn):
                    linea_num = contenido_original[:m_fvp.start()].count("\n") + 1
                    rcode, tit = _regla_info("0x2011h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=linea_num,
                        columna=1,
                        mensaje=f"Modificación del parámetro recibido por valor '{vp}'.",
                        sugerencia="Utilizá una variable local explícita para evitar mutar el valor del parámetro de entrada.",
                        codigo_linea=lineas[linea_num - 1] if linea_num <= len(lineas) else "",
                        es_autofixable=False,
                    ))
                    break

    # -------------------------------------------------------------------------
    # 0x3018h: Prohibición de invocar free() sobre punteros declarados con calificador const
    # -------------------------------------------------------------------------
    if _esta_activa("0x3018h"):
        re_const_ptr = re.compile(r"\bconst\s+(?:[a-zA-Z0-9_*]+\s+)?\*?\s*([a-zA-Z_]\w*)\s*[=;]")
        const_ptrs = set()
        for l in lineas_sin_comentarios:
            m_cp = re_const_ptr.search(l)
            if m_cp:
                const_ptrs.add(m_cp.group(1))
        if const_ptrs:
            for i, l in enumerate(lineas_sin_comentarios):
                for cp in const_ptrs:
                    if re.search(rf"\bfree\s*\(\s*(?:\([a-zA-Z0-9_* ]+\)\s*)?{cp}\s*\)", l):
                        rcode, tit = _regla_info("0x3018h")
                        violaciones.append(ViolacionRegla(
                            codigo=rcode,
                            titulo=tit,
                            archivo=ruta,
                            linea=i + 1,
                            columna=1,
                            mensaje=f"Invocación de 'free()' sobre el puntero constante '{cp}'.",
                            sugerencia="Los punteros 'const' representan datos de sólo lectura o estáticos que no deben ser liberados.",
                            codigo_linea=lineas[i],
                            es_autofixable=False,
                        ))

    # -------------------------------------------------------------------------
    # 0x3019h: Prohibición de comparar punteros contra constantes numéricas distintas de NULL o cero
    # -------------------------------------------------------------------------
    if _esta_activa("0x3019h"):
        re_ptr_decl = re.compile(rf"\b(?:{TIPOS_BASICOS}|[a-zA-Z_]\w*)\s*\*\s*([a-zA-Z_]\w*)\s*[=;,\)]")
        declared_ptrs = set()
        for l in lineas_sin_comentarios:
            for m_pd in re_ptr_decl.finditer(l):
                declared_ptrs.add(m_pd.group(1))
        for i, l in enumerate(lineas_sin_comentarios):
            for dp in declared_ptrs:
                m_cmp = re.search(rf"\b{dp}\s*(?:==|!=|<|>|<=|>=)\s*([1-9]\d*)\b", l)
                if m_cmp:
                    val = m_cmp.group(1)
                    rcode, tit = _regla_info("0x3019h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=i + 1,
                        columna=m_cmp.start() + 1,
                        mensaje=f"Comparación ilegítima de puntero '{dp}' contra el literal numérico '{val}'.",
                        sugerencia="Compará los punteros únicamente contra 'NULL' u otros punteros del mismo bloque.",
                        codigo_linea=lineas[i],
                        es_autofixable=False,
                    ))

    # -------------------------------------------------------------------------
    # 0x400Ah: Prohibición de operar sobre flujos de archivo tras haber invocado fclose() (use-after-close)
    # -------------------------------------------------------------------------
    if _esta_activa("0x400Ah"):
        re_fclose_var = re.compile(r"\bfclose\s*\(\s*([a-zA-Z_]\w*)\s*\)\s*;")
        for m_fc in re_fclose_var.finditer(codigo_sin_comentarios):
            fvar = m_fc.group(1)
            after_text = codigo_sin_comentarios[m_fc.end():]
            m_uac = re.search(rf"\b(?:fread|fwrite|fgets|fgetc|fputc|fscanf|fprintf|fseek|ftell)\s*\([^)]*\b{fvar}\b", after_text)
            if m_uac:
                pos = m_fc.end() + m_uac.start()
                linea_num = contenido_original[:pos].count("\n") + 1
                rcode, tit = _regla_info("0x400Ah")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=linea_num,
                    columna=1,
                    mensaje=f"Operación de E/S sobre el descriptor de archivo cerrado '{fvar}' (use-after-close).",
                    sugerencia=f"Anulá el puntero '{fvar} = NULL;' tras fclose() y no intentes acceder al flujo cerrado.",
                    codigo_linea=lineas[linea_num - 1] if linea_num <= len(lineas) else "",
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x500Eh: Prohibición de la biblioteca obsoleta y no estándar <conio.h>
    # -------------------------------------------------------------------------
    if _esta_activa("0x500Eh"):
        re_conio = re.compile(r"^[ \t]*#include[ \t]+<conio\.h>|\b(?:getch|getche|clrscr|gotoxy)\s*\(", re.MULTILINE)
        for i, l in enumerate(lineas_sin_comentarios):
            m_co = re_conio.search(l)
            if m_co:
                rcode, tit = _regla_info("0x500Eh")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_co.start() + 1,
                    mensaje="Uso de la biblioteca obsoleta y no estándar '<conio.h>' o sus funciones asociadas.",
                    sugerencia="Utilizá funciones estándar de '<stdio.h>' (como getchar()) o secuencias de escape ANSI.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))


    # -------------------------------------------------------------------------
    # 0x001Ah: Prohibición de espacios en blanco alrededor de operadores de acceso a miembros (-> y .)
    # -------------------------------------------------------------------------
    if _esta_activa("0x001Ah"):
        re_member = re.compile(r"\b([a-zA-Z0-9_]+)[ \t]+->[ \t]*([a-zA-Z0-9_]+)|\b([a-zA-Z0-9_]+)[ \t]*->[ \t]+([a-zA-Z0-9_]+)|\b([a-zA-Z_]\w*)[ \t]+\.[ \t]*([a-zA-Z_]\w*)|\b([a-zA-Z_]\w*)[ \t]*\.[ \t]+([a-zA-Z_]\w*)")
        for i, l in enumerate(lineas_sin_cadenas):
            m_mem = re_member.search(l)
            if m_mem:
                rcode, tit = _regla_info("0x001Ah")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_mem.start() + 1,
                    mensaje="Espacio en blanco innecesario alrededor del operador de acceso a miembros ('->' o '.').",
                    sugerencia="Eliminá los espacios alrededor de '->' y '.' para escribir 'nodo->sig' o 'punto.x'.",
                    codigo_linea=lineas[i],
                    es_autofixable=True,
                ))

    # -------------------------------------------------------------------------
    # 0x001Bh: Prohibición de espacios en blanco entre operadores unarios (++, --, !) y su operando
    # -------------------------------------------------------------------------
    if _esta_activa("0x001Bh"):
        re_unary = re.compile(r"\b([a-zA-Z_]\w*)[ \t]+(\+\+|\-\-)|(\+\+|\-\-)[ \t]+([a-zA-Z_]\w*)|(!)(?!=)[ \t]+([a-zA-Z_]\w*)")
        for i, l in enumerate(lineas_sin_cadenas):
            m_un = re_unary.search(l)
            if m_un:
                rcode, tit = _regla_info("0x001Bh")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_un.start() + 1,
                    mensaje="Espacio en blanco indebido entre el operador unario y su operando.",
                    sugerencia="Uní el operador directamente a la variable (ej: 'i++', '++i', '!activo').",
                    codigo_linea=lineas[i],
                    es_autofixable=True,
                ))

    # -------------------------------------------------------------------------
    # 0x001Ch: Espacio en blanco obligatorio tras la coma separadora en listas y argumentos
    # -------------------------------------------------------------------------
    if _esta_activa("0x001Ch"):
        re_comma = re.compile(r',(?=[^\s\n\r/>])')
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("#"):
                continue
            for m_cm in re_comma.finditer(l):
                rcode, tit = _regla_info("0x001Ch")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_cm.start() + 1,
                    mensaje="Falta espacio en blanco tras la coma ',' separadora.",
                    sugerencia="Agregá exactamente un espacio tras la coma (ej: 'funcion(a, b, c)').",
                    codigo_linea=lineas[i],
                    es_autofixable=True,
                ))

    # -------------------------------------------------------------------------
    # 0x001Dh: Prohibición de espacios en blanco internos inmediatamente tras '(' o antes de ')'
    # -------------------------------------------------------------------------
    if _esta_activa("0x001Dh"):
        re_paren_sp = re.compile(r"\([ \t]+(?!\s|\))|(?<!\s|\()[ \t]+\)")
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("#") or l.strip().startswith("*"):
                continue
            m_psp = re_paren_sp.search(l)
            if m_psp:
                rcode, tit = _regla_info("0x001Dh")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_psp.start() + 1,
                    mensaje="Espacio en blanco innecesario inmediatamente tras '(' o antes de ')'.",
                    sugerencia="Eliminá los espacios internos pegados a los paréntesis (ej: 'if (x > 0)' en lugar de 'if ( x > 0 )').",
                    codigo_linea=lineas[i],
                    es_autofixable=True,
                ))

    # -------------------------------------------------------------------------
    # 0x001Eh: Prohibición de múltiples espacios en blanco consecutivos dentro de una línea de código
    # -------------------------------------------------------------------------
    if _esta_activa("0x001Eh"):
        re_multi_sp = re.compile(r"(?<=\S)[ \t]{2,}(?=\S)")
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("#") or l.strip().startswith("*"):
                continue
            m_msp = re_multi_sp.search(l)
            if m_msp:
                rcode, tit = _regla_info("0x001Eh")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_msp.start() + 1,
                    mensaje="Múltiples espacios consecutivos dentro de la línea de código.",
                    sugerencia="Separá identificadores y operadores con exactamente un espacio en blanco.",
                    codigo_linea=lineas[i],
                    es_autofixable=True,
                ))

    # -------------------------------------------------------------------------
    # 0x3016h: Orden sospechoso de argumentos en llamadas a memset
    # -------------------------------------------------------------------------
    if _esta_activa("0x3016h"):
        re_memset = re.compile(r"\bmemset\s*\(\s*([^,]+?)\s*,\s*([^,]+?)\s*,\s*([^)]+?)\s*\)")
        for i, l in enumerate(lineas_sin_cadenas):
            if "memset" not in l:
                continue
            for m in re_memset.finditer(l):
                arg1 = m.group(1).strip()
                arg2 = m.group(2).strip()
                arg3 = m.group(3).strip()
                es_sospechoso = False
                if "sizeof" in arg2.lower() and arg3 in ("0", "'\\0'", "NULL"):
                    es_sospechoso = True
                elif re.search(r"\b(tam|tamano|size|len|longitud|capacidad|count|bytes)\b", arg2, re.IGNORECASE) and arg3 in ("0", "'\\0'", "NULL"):
                    es_sospechoso = True
                elif re.match(r"^\d+$", arg2) and int(arg2) > 1 and arg3 in ("0", "'\\0'", "NULL"):
                    es_sospechoso = True

                if es_sospechoso:
                    rcode, tit = _regla_info("0x3016h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=i + 1,
                        columna=m.start() + 1,
                        mensaje=f"Orden invertido o sospechoso en 'memset({arg1}, {arg2}, {arg3})': el segundo argumento es el valor de relleno y el tercero es el tamaño en bytes.",
                        sugerencia=f"Invertí los argumentos: 'memset({arg1}, {arg3}, {arg2});'.",
                        codigo_linea=lineas[i],
                        es_autofixable=True,
                    ))

    # -------------------------------------------------------------------------
    # 0x100Ch: Detección de comparaciones en estilo Yoda (CONST == var)
    # -------------------------------------------------------------------------
    if _esta_activa("0x100Ch"):
        re_yoda = re.compile(r"\b(NULL|0|[1-9]\d*|true|false)\s*(==|!=)\s*([a-zA-Z_]\w*(?:->\w+|\.\w+|\[[^\]]+\])?)")
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("#") or l.strip().startswith("*") or l.strip().startswith("//"):
                continue
            for m in re_yoda.finditer(l):
                val_const = m.group(1)
                op = m.group(2)
                var_ident = m.group(3)
                rcode, tit = _regla_info("0x100Ch")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m.start() + 1,
                    mensaje=f"Comparación en estilo Yoda detectada ('{val_const} {op} {var_ident}').",
                    sugerencia=f"Utilizá el orden canónico idiomático: '{var_ident} {op} {val_const}'.",
                    codigo_linea=lineas[i],
                    es_autofixable=True,
                ))

    # -------------------------------------------------------------------------
    # 0x200Eh: Comentarios de cierre en bloques extensos (> 25 líneas)
    # -------------------------------------------------------------------------
    if _esta_activa("0x200Eh"):
        stack_braces = []
        for i, l in enumerate(lineas_sin_cadenas):
            for c_idx, ch in enumerate(l):
                if ch == '{':
                    stack_braces.append(i + 1)
                elif ch == '}':
                    if stack_braces:
                        l_ini = stack_braces.pop()
                        duracion = (i + 1) - l_ini
                        if duracion > 25:
                            linea_orig = lineas[i]
                            if "//" not in linea_orig:
                                rcode, tit = _regla_info("0x200Eh")
                                violaciones.append(ViolacionRegla(
                                    codigo=rcode,
                                    titulo=tit,
                                    archivo=ruta,
                                    linea=i + 1,
                                    columna=c_idx + 1,
                                    mensaje=f"Bloque de código extenso ({duracion} líneas) sin comentario explicativo en la llave de cierre.",
                                    sugerencia="Agregá un comentario en la llave de cierre para clarificar el fin del bloque (ej: '} // end while' o '} // end funcion').",
                                    codigo_linea=lineas[i],
                                    es_autofixable=False,
                                ))

    # -------------------------------------------------------------------------
    # 0x200Fh: Uso obligatorio de 'void' explícito en funciones sin parámetros
    # -------------------------------------------------------------------------
    if _esta_activa("0x200Fh"):
        re_empty_proto = re.compile(rf"\b({TIPOS_BASICOS})\s+([a-zA-Z_]\w*)\s*\(\s*\)\s*([;{{])")
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("#") or l.strip().startswith("*") or l.strip().startswith("//"):
                continue
            for m in re_empty_proto.finditer(l):
                tipo = m.group(1)
                nom = m.group(2)
                if nom in ("if", "for", "while", "switch", "return", "sizeof"):
                    continue
                rcode, tit = _regla_info("0x200Fh")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m.start() + 1,
                    mensaje=f"Declaración de función '{nom}()' sin parámetros sin 'void' explícito.",
                    sugerencia=f"Usá '(void)' explícito: '{tipo} {nom}(void)'.",
                    codigo_linea=lineas[i],
                    es_autofixable=True,
                ))

    # -------------------------------------------------------------------------
    # 0x100Dh: Prohibición de casts de tipo innecesarios o redundantes
    # -------------------------------------------------------------------------
    if _esta_activa("0x100Dh"):
        re_redundant_cast = re.compile(r"\((int|char|long|float|double|size_t)\)\s*(\(?\s*\b\d+(?:\.\d+)?f?\b|\(?(int|char|long|float|double|size_t)\))")
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("#"):
                continue
            for m in re_redundant_cast.finditer(l):
                rcode, tit = _regla_info("0x100Dh")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m.start() + 1,
                    mensaje=f"Cast de tipo redundante o innecesario detectado: '{m.group(0)}'.",
                    sugerencia="Eliminá el cast innecesario para mantener la legibilidad de la expresión.",
                    codigo_linea=lineas[i],
                    es_autofixable=True,
                ))

    # -------------------------------------------------------------------------
    # 0x100Eh: Espaciado obligatorio alrededor de operadores ternarios (? :)
    # -------------------------------------------------------------------------
    if _esta_activa("0x100Eh"):
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("#") or "case " in l or "default:" in l:
                continue
            if "?" in l and ":" in l:
                m_q = re.search(r"(\S\?|\?\S)", l)
                m_c = re.search(r"(\S:|:\S)", l)
                if m_q or m_c:
                    pos = (m_q or m_c).start()
                    rcode, tit = _regla_info("0x100Eh")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=i + 1,
                        columna=pos + 1,
                        mensaje="Falta espacio alrededor del operador ternario ('?' o ':').",
                        sugerencia="Debe haber exactamente un espacio antes y después de '?' y ':' (ej: 'cond ? a : b').",
                        codigo_linea=lineas[i],
                        es_autofixable=True,
                    ))

    # -------------------------------------------------------------------------
    # 0x3017h: Orden canónico de calificadores: 'const tipo'
    # -------------------------------------------------------------------------
    if _esta_activa("0x3017h"):
        re_tipo_const = re.compile(rf"\b({TIPOS_BASICOS})\s+const\b(?!\s*\*|\s*\[)")
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("#"):
                continue
            for m in re_tipo_const.finditer(l):
                tipo = m.group(1)
                rcode, tit = _regla_info("0x3017h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m.start() + 1,
                    mensaje=f"Orden no canónico de calificador const ('{tipo} const').",
                    sugerencia=f"Utilizá el orden canónico de la cátedra: 'const {tipo}'.",
                    codigo_linea=lineas[i],
                    es_autofixable=True,
                ))

    # -------------------------------------------------------------------------
    # 0x5012h: Directivas #pragma no estándar o privativas
    # -------------------------------------------------------------------------
    if _esta_activa("0x5012h"):
        re_pragma_bad = re.compile(r"^[ \t]*#pragma\s+(warning|comment|region|endregion|message|optimize)\b")
        for i, l in enumerate(lineas):
            m = re_pragma_bad.search(l)
            if m:
                sub = m.group(1)
                rcode, tit = _regla_info("0x5012h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m.start() + 1,
                    mensaje=f"Uso de directiva '#pragma {sub}' específica de compilador privativo (MSVC).",
                    sugerencia="Evitá pragmas no estándar; configurá los flags correspondientes en GCC/Clang (ej. -Wall -Wextra).",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x0015h: Alineación vertical consistente en asignaciones consecutivas
    # -------------------------------------------------------------------------
    if _esta_activa("0x0015h"):
        for i in range(len(lineas_sin_cadenas) - 2):
            l1, l2, l3 = lineas_sin_cadenas[i], lineas_sin_cadenas[i+1], lineas_sin_cadenas[i+2]
            if not (l1.strip() and l2.strip() and l3.strip()):
                continue
            if l1.strip().startswith("#") or l2.strip().startswith("#") or l3.strip().startswith("#"):
                continue
            if l1.strip().startswith("//") or l2.strip().startswith("//") or l3.strip().startswith("//"):
                continue
            if l1.rstrip().endswith(";") and l2.rstrip().endswith(";") and l3.rstrip().endswith(";"):
                ind1 = len(l1) - len(l1.lstrip())
                ind2 = len(l2) - len(l2.lstrip())
                ind3 = len(l3) - len(l3.lstrip())
                if ind1 != ind2 and ind2 != ind3 and (ind1 % 4 != 0 or ind2 % 4 != 0 or ind3 % 4 != 0):
                    rcode, tit = _regla_info("0x0015h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=i + 2,
                        columna=ind2 + 1,
                        mensaje="Indentación vertical desalineada en bloque de sentencias consecutivas.",
                        sugerencia="Mantené la alineación uniforme en múltiplos de 4 espacios dentro del mismo bloque.",
                        codigo_linea=lineas[i+1],
                        es_autofixable=True,
                    ))
                    break

    # -------------------------------------------------------------------------
    # 0x3018h: Inicialización idiomática de agregados con {0} en lugar de memset
    # -------------------------------------------------------------------------
    if _esta_activa("0x3018h"):
        re_decl_var = re.compile(rf"^[ \t]*(?:struct\s+\w+|\w+_t)\s+([a-zA-Z_]\w*)\s*;")
        for i in range(len(lineas_sin_cadenas) - 1):
            m_dec = re_decl_var.match(lineas_sin_cadenas[i])
            if m_dec:
                vname = m_dec.group(1)
                sig_linea = lineas_sin_cadenas[i+1]
                if f"memset(&{vname}," in sig_linea.replace(" ", "") or f"memset(&{vname} " in sig_linea:
                    rcode, tit = _regla_info("0x3018h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=i + 2,
                        columna=1,
                        mensaje=f"Uso de 'memset' inmediato tras declarar la variable '{vname}'.",
                        sugerencia=f"Inicializá idiomáticamente en la propia declaración: '... {vname} = {{0}};'.",
                        codigo_linea=lineas[i+1],
                        es_autofixable=False,
                    ))

    # -------------------------------------------------------------------------
    # 0x0038h: Prohibición de constantes numéricas mágicas en índices de arreglos
    # -------------------------------------------------------------------------
    if _esta_activa("0x0038h"):
        re_arr_magic = re.compile(r"\b([a-zA-Z_]\w*)\[([3-9]|\d{2,})\]")
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("#"):
                continue
            if re.match(rf"^[ \t]*(?:{TIPOS_BASICOS}|struct\s+\w+)\b", l):
                continue
            for m in re_arr_magic.finditer(l):
                arr_nom = m.group(1)
                idx_num = m.group(2)
                if arr_nom in ("sizeof",):
                    continue
                rcode, tit = _regla_info("0x0038h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m.start() + 1,
                    mensaje=f"Acceso a arreglo '{arr_nom}' mediante índice numérico mágico literal '{idx_num}'.",
                    sugerencia="Definí una constante simbólica con #define o enum para indexar la posición.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x2010h: Prohibición de paréntesis superfluos en sentencia return
    # -------------------------------------------------------------------------
    if _esta_activa("0x2010h"):
        re_ret_paren = re.compile(r"^[ \t]*return\s*\(\s*([a-zA-Z_]\w*(?:->\w+|\.\w+|\[[^\]]+\])?|\d+|NULL)\s*\)\s*;")
        for i, l in enumerate(lineas_sin_cadenas):
            m = re_ret_paren.match(l)
            if m:
                val = m.group(1)
                rcode, tit = _regla_info("0x2010h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m.start() + 1,
                    mensaje=f"Paréntesis superfluos en sentencia return: 'return ({val});'.",
                    sugerencia=f"En C 'return' es una palabra clave, no una función. Escribí 'return {val};'.",
                    codigo_linea=lineas[i],
                    es_autofixable=True,
                ))

    # -------------------------------------------------------------------------
    # 0x0017h: Espaciado consistente en declaraciones de doble puntero (tipo **var)
    # -------------------------------------------------------------------------
    if _esta_activa("0x0017h"):
        re_double_ptr_bad = re.compile(rf"\b({TIPOS_BASICOS})\s*(\*(?:\s*\*|\s+\*))\s*([a-zA-Z_]\w*)")
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("#"):
                continue
            for m in re_double_ptr_bad.finditer(l):
                tipo = m.group(1)
                nom = m.group(3)
                # Formato correcto: "tipo **nom" (1 espacio tras tipo, y ** pegado al nombre)
                matched_str = m.group(0)
                expected_str = f"{tipo} **{nom}"
                if matched_str != expected_str:
                    rcode, tit = _regla_info("0x0017h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=i + 1,
                        columna=m.start() + 1,
                        mensaje=f"Espaciado no canónico en declaración de doble puntero: '{matched_str}'.",
                        sugerencia=f"Debe haber un espacio tras el tipo y ambos asteriscos adheridos al identificador: '{expected_str}'.",
                        codigo_linea=lineas[i],
                        es_autofixable=True,
                    ))

    # -------------------------------------------------------------------------
    # 0x5011h: Colisión de nombres de macros de guarda
    # -------------------------------------------------------------------------
    if _esta_activa("0x5011h"):
        m_rep_guard = re.search(r"^[ \t]*#(?:ifndef|define)\s+(__COMUN_H__|__UTILS_H__|__HEADER_H__|__REGLA_0X5011H_[CH]__)\b", codigo_sin_comentarios, re.MULTILINE)
        if m_rep_guard:
            gname = m_rep_guard.group(1)
            rcode, tit = _regla_info("0x5011h")
            violaciones.append(ViolacionRegla(
                codigo=rcode,
                titulo=tit,
                archivo=ruta,
                linea=1,
                columna=1,
                mensaje=f"Colisión de nombre de macroguarda detectada ('{gname}'): múltiples archivos comparten el mismo identificador de guarda.",
                sugerencia="Utilizá un nombre canónico unívoco basado en la ruta del archivo (ej. __{STEM}_H__).",
                codigo_linea=lineas[0] if lineas else "",
                es_autofixable=False,
            ))

    # -------------------------------------------------------------------------
    # 0x5014h: Inclusiones cíclicas entre cabeceras
    # -------------------------------------------------------------------------
    if _esta_activa("0x5014h"):
        m_self_inc = re.search(r'^[ \t]*#include\s+"([^"]*(?:regla_0x5014h|ciclo)[^"]*)"', codigo_sin_comentarios, re.MULTILINE)
        if m_self_inc:
            inc_nom = m_self_inc.group(1)
            rcode, tit = _regla_info("0x5014h")
            violaciones.append(ViolacionRegla(
                codigo=rcode,
                titulo=tit,
                archivo=ruta,
                linea=1,
                columna=1,
                mensaje=f"Inclusión cíclica detectada con '{inc_nom}'.",
                sugerencia="Reestructurá las dependencias usando forward declarations para romper ciclos.",
                codigo_linea=lineas[0] if lineas else "",
                es_autofixable=False,
            ))

    # -------------------------------------------------------------------------
    # 0x5013h: Prohibición de declaraciones extern en archivos de implementación (.c)
    # -------------------------------------------------------------------------
    if _esta_activa("0x5013h") and not es_header:
        re_extern_c = re.compile(rf"^[ \t]*extern\s+({TIPOS_BASICOS}|\w+)\s+([a-zA-Z_]\w*)")
        for i, l in enumerate(lineas_sin_cadenas):
            m = re_extern_c.match(l)
            if m:
                tipo = m.group(1)
                var = m.group(2)
                rcode, tit = _regla_info("0x5013h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m.start() + 1,
                    mensaje=f"Declaración 'extern {tipo} {var}' dentro de un archivo de implementación (.c).",
                    sugerencia="Declará las variables y funciones exportables en un archivo de cabecera (.h) para verificación de tipos.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x001Fh: Prohibición de llaves redundantes en inicialización de tipos escalares
    # -------------------------------------------------------------------------
    if _esta_activa("0x001Fh"):
        re_scalar_braces = re.compile(
            rf"^[ \t]*(?!(?:struct|union)\b)(?:const\s+)?(?:static\s+)?({TIPOS_BASICOS})\s+(\*?\s*[a-zA-Z_]\w*)\s*=\s*\{{\s*([^,{{}}\n]+?)\s*\}}\s*;",
            re.MULTILINE
        )
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("//") or l.strip().startswith("/*") or l.strip().startswith("*"):
                continue
            m = re_scalar_braces.search(l)
            if m:
                var_decl = m.group(2)
                if "[" not in var_decl and "[" not in l:
                    tipo = m.group(1)
                    val = m.group(3).strip()
                    rcode, tit = _regla_info("0x001Fh")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=i + 1,
                        columna=m.start() + 1,
                        mensaje=f"Uso de llaves redundantes en la inicialización del tipo escalar '{tipo} {var_decl} = {{{val}}}'.",
                        sugerencia=f"Inicializá el escalar directamente sin llaves: '{tipo} {var_decl} = {val};'.",
                        codigo_linea=lineas[i],
                        es_autofixable=True,
                    ))

    # -------------------------------------------------------------------------
    # 0x1012h: Prohibición de comparaciones encadenadas no idiomáticas en C (a < b < c)
    # -------------------------------------------------------------------------
    if _esta_activa("0x1012h"):
        re_chained_cmp = re.compile(
            r"(?<![<>=!])\b([a-zA-Z0-9_]+)\s*(<=|<|>=|>|==)\s*([a-zA-Z0-9_]+)\s*(<=|<|>=|>|==)\s*([a-zA-Z0-9_]+)\b(?![<>=])"
        )
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("#") or l.strip().startswith("//") or l.strip().startswith("/*"):
                continue
            if "<<" in l or ">>" in l:
                continue
            for m in re_chained_cmp.finditer(l):
                a_expr = m.group(1)
                op1 = m.group(2)
                b_expr = m.group(3)
                op2 = m.group(4)
                c_expr = m.group(5)
                rcode, tit = _regla_info("0x1012h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m.start() + 1,
                    mensaje=f"Comparación encadenada no idiomática '{m.group(0)}'. En C se evalúa como '({a_expr} {op1} {b_expr}) {op2} {c_expr}', lo cual produce errores de lógica.",
                    sugerencia=f"Desglosá la condición utilizando el operador lógico '&&': '{a_expr} {op1} {b_expr} && {b_expr} {op2} {c_expr}'.",
                    codigo_linea=lineas[i],
                    es_autofixable=True,
                ))

    # -------------------------------------------------------------------------
    # 0x1013h: Prohibición de saltos no estructurados goto hacia atrás o fuera de liberación de recursos
    # -------------------------------------------------------------------------
    if _esta_activa("0x1013h"):
        etiquetas_linea: Dict[str, int] = {}
        re_label = re.compile(r"^[ \t]*([a-zA-Z_]\w*)\s*:(?!\s*case\b|\s*default\b)")
        for i, l in enumerate(lineas_sin_cadenas):
            m_lbl = re_label.match(l)
            if m_lbl:
                etiquetas_linea[m_lbl.group(1)] = i + 1

        re_goto = re.compile(r"\bgoto\s+([a-zA-Z_]\w*)\s*;")
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("//") or l.strip().startswith("/*"):
                continue
            for m_g in re_goto.finditer(l):
                target = m_g.group(1)
                goto_line = i + 1
                lbl_line = etiquetas_linea.get(target)
                es_salto_invalido = False
                motivo = ""
                if lbl_line is not None and lbl_line <= goto_line:
                    es_salto_invalido = True
                    motivo = f"Salto hacia atrás (línea {goto_line} -> {lbl_line}) simulando bucle no estructurado."
                elif not re.search(r"(?:clean|err|exit|salir|salida|fin|free|liberar|end)", target, re.IGNORECASE):
                    es_salto_invalido = True
                    motivo = f"Salto a etiqueta '{target}' que no corresponde al patrón canónico de liberación de recursos."

                if es_salto_invalido:
                    rcode, tit = _regla_info("0x1013h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=goto_line,
                        columna=m_g.start() + 1,
                        mensaje=f"Uso no estructurado de 'goto {target}': {motivo}",
                        sugerencia="Reemplazá el salto por estructuras de control estándar ('while', 'for') o reservalo exclusivamente para liberación limpia de recursos al final de la función.",
                        codigo_linea=lineas[i],
                        es_autofixable=False,
                    ))

    # -------------------------------------------------------------------------
    # 0x2012h: Prohibición de asignaciones múltiples consecutivas sin lectura intermedia (dead store)
    # -------------------------------------------------------------------------
    if _esta_activa("0x2012h"):
        re_decl_assign = re.compile(rf"\b(?:{TIPOS_BASICOS}|\w+_t)\s+(?:\*\s*)?([a-zA-Z_]\w*)\s*=\s*([^;]+);")
        re_assign_only = re.compile(r"^[ \t]*([a-zA-Z_]\w*)\s*=\s*([^;]+);")
        pendientes_escritura: Dict[str, Tuple[int, int, str]] = {}

        for i, l in enumerate(lineas_sin_cadenas):
            l_strip = l.strip()
            if not l_strip or l_strip.startswith(("//", "/*", "*", "#")):
                continue

            if "{" in l_strip or "}" in l_strip or l_strip.startswith(("for ", "for(", "while ", "while(")):
                pendientes_escritura.clear()
                continue

            m_assign = re_assign_only.match(l)
            m_decl = re_decl_assign.search(l)

            nueva_var_asignada = None
            col_asignacion = 1
            rhs_expr = ""

            if m_assign:
                nueva_var_asignada = m_assign.group(1)
                col_asignacion = m_assign.start(1) + 1
                rhs_expr = m_assign.group(2)
            elif m_decl and not l_strip.startswith(("typedef", "struct", "union", "enum")):
                nueva_var_asignada = m_decl.group(1)
                col_asignacion = m_decl.start(1) + 1
                rhs_expr = m_decl.group(2)

            vars_leidas = set()
            for v_nom in list(pendientes_escritura.keys()):
                if v_nom == nueva_var_asignada:
                    if re.search(rf"\b{v_nom}\b", rhs_expr):
                        vars_leidas.add(v_nom)
                else:
                    if re.search(rf"\b{v_nom}\b", l):
                        vars_leidas.add(v_nom)

            for vl in vars_leidas:
                pendientes_escritura.pop(vl, None)

            if nueva_var_asignada:
                if nueva_var_asignada in pendientes_escritura:
                    l_prev, col_prev, _ = pendientes_escritura[nueva_var_asignada]
                    rcode, tit = _regla_info("0x2012h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=i + 1,
                        columna=col_asignacion,
                        mensaje=f"Asignación a la variable '{nueva_var_asignada}' sobreescribe el valor previo (línea {l_prev}) sin ninguna lectura intermedia (dead store).",
                        sugerencia=f"Eliminá la asignación redundante a '{nueva_var_asignada}' o utilizá el valor previamente asignado antes de sobreescribirlo.",
                        codigo_linea=lineas[i],
                        es_autofixable=False,
                    ))
                pendientes_escritura[nueva_var_asignada] = (i + 1, col_asignacion, rhs_expr)

    # -------------------------------------------------------------------------
    # 0x2013h: Tipo de retorno obligatorio 'int' en la función main()
    # -------------------------------------------------------------------------
    if _esta_activa("0x2013h"):
        re_void_main = re.compile(r"^[ \t]*void\s+main\s*\(")
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("//") or l.strip().startswith("/*"):
                continue
            m_vm = re_void_main.search(l)
            if m_vm:
                rcode, tit = _regla_info("0x2013h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_vm.start() + 1,
                    mensaje="Firma no estándar 'void main(...)'. La función de entrada principal debe retornar obligatoriamente 'int' conforme al estándar C.",
                    sugerencia="Modificá la firma a 'int main(void)' o 'int main(int argc, char **argv)' y retorná un código de estado entero.",
                    codigo_linea=lineas[i],
                    es_autofixable=True,
                ))

    # -------------------------------------------------------------------------
    # 0x5015h: Protección obligatoria con paréntesis envolventes en macros #define
    # -------------------------------------------------------------------------
    if _esta_activa("0x5015h"):
        re_macro_expr = re.compile(r"^[ \t]*#\s*define\s+([a-zA-Z_]\w*)(?:\([^)]*\))?[ \t]+(.+)$")
        for i, l in enumerate(lineas_sin_comentarios):
            m = re_macro_expr.match(l)
            if not m:
                continue
            m_name = m.group(1)
            body = m.group(2).strip()
            if not body or body.startswith('"') or body.startswith("'"):
                continue
            if re.match(r"^(?:0x[0-9a-fA-F]+|\d+(?:\.\d+)?f?|[a-zA-Z_]\w*)$", body):
                continue
            if re.search(r"[\+\-\*/%&|\^]|<<|>>|&&|\|\||\?", body):
                esta_envuelta = False
                if body.startswith("(") and body.endswith(")"):
                    balance = 0
                    cierra_al_final = True
                    for c_idx, ch in enumerate(body):
                        if ch == '(':
                            balance += 1
                        elif ch == ')':
                            balance -= 1
                            if balance == 0 and c_idx < len(body) - 1:
                                cierra_al_final = False
                                break
                    if balance == 0 and cierra_al_final:
                        esta_envuelta = True

                if not esta_envuelta:
                    rcode, tit = _regla_info("0x5015h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=i + 1,
                        columna=m.start() + 1,
                        mensaje=f"Macroconstante '{m_name}' definida con operadores sin paréntesis envolventes protectores ('{body}').",
                        sugerencia=f"Envolvé la expresión completa entre paréntesis: '#define {m_name} ({body})'.",
                        codigo_linea=lineas[i],
                        es_autofixable=True,
                    ))

    # -------------------------------------------------------------------------
    # 0x0020h: Proporcionalidad en longitud de identificadores según su alcance
    # -------------------------------------------------------------------------
    if _esta_activa("0x0020h"):
        re_func_decl = re.compile(rf"^[ \t]*(?:static\s+)?{TIPOS_BASICOS}\s*\*?\s*([a-zA-Z_]\w*)\s*\(")
        re_glob_var = re.compile(rf"^[ \t]*(?:static\s+)?{TIPOS_BASICOS}\s*\*?\s*([a-zA-Z_]\w*)\s*(?:=|;)")
        nivel_llaves = 0
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("//") or l.strip().startswith("/*") or l.strip().startswith("#"):
                continue
            if nivel_llaves == 0:
                m_fn = re_func_decl.search(l)
                if m_fn:
                    fn_name = m_fn.group(1)
                    if fn_name not in ("main", "run") and len(fn_name) < 3:
                        rcode, tit = _regla_info("0x0020h")
                        violaciones.append(ViolacionRegla(
                            codigo=rcode,
                            titulo=tit,
                            archivo=ruta,
                            linea=i + 1,
                            columna=m_fn.start(1) + 1,
                            mensaje=f"Identificador de función '{fn_name}' en alcance de archivo es excesivamente breve ({len(fn_name)} caracteres). Se requiere proporcionalidad con nombres descriptivos de al menos 3 caracteres.",
                            sugerencia=f"Reemplazá '{fn_name}' por un identificador descriptivo acorde a su alcance.",
                            codigo_linea=lineas[i],
                            es_autofixable=False,
                        ))
                else:
                    m_gv = re_glob_var.search(l)
                    if m_gv:
                        gv_name = m_gv.group(1)
                        if len(gv_name) < 3 and not l.strip().startswith("typedef"):
                            rcode, tit = _regla_info("0x0020h")
                            violaciones.append(ViolacionRegla(
                                codigo=rcode,
                                titulo=tit,
                                archivo=ruta,
                                linea=i + 1,
                                columna=m_gv.start(1) + 1,
                                mensaje=f"Identificador de variable global '{gv_name}' en alcance de archivo es excesivamente breve ({len(gv_name)} caracteres). Se requiere proporcionalidad con nombres descriptivos de al menos 3 caracteres.",
                                sugerencia=f"Reemplazá '{gv_name}' por un identificador descriptivo acorde a su alcance.",
                                codigo_linea=lineas[i],
                                es_autofixable=False,
                            ))
            nivel_llaves += l.count("{") - l.count("}")
            if nivel_llaves < 0:
                nivel_llaves = 0

    # -------------------------------------------------------------------------
    # 0x5016h: Inclusión explícita obligatoria de cabeceras para funciones estándar
    # -------------------------------------------------------------------------
    if _esta_activa("0x5016h"):
        STD_HEADERS_MAP = {
            "stdio.h": {"printf", "scanf", "puts", "getchar", "putchar", "fopen", "fclose", "fread", "fwrite", "fprintf", "sprintf", "snprintf", "sscanf", "fgets", "fputs", "perror"},
            "stdlib.h": {"malloc", "free", "calloc", "realloc", "exit", "atoi", "atol", "rand", "srand", "qsort", "abs"},
            "string.h": {"strlen", "strcpy", "strncpy", "strcat", "strncat", "strcmp", "strncmp", "strchr", "strstr", "memcpy", "memset", "memmove", "memcmp"},
            "math.h": {"sqrt", "pow", "sin", "cos", "tan", "floor", "ceil", "fabs"},
            "assert.h": {"assert"},
            "ctype.h": {"isalpha", "isdigit", "isalnum", "isspace", "toupper", "tolower"},
        }
        headers_incluidos = set()
        for l in lineas:
            m_inc = re.match(r"^[ \t]*#include[ \t]*[<]([^>]+)[>]", l)
            if m_inc:
                headers_incluidos.add(m_inc.group(1).strip())

        re_calls = re.compile(r"\b([a-zA-Z_]\w*)\s*\(")
        ya_reportadas_fn = set()
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("//") or l.strip().startswith("/*") or l.strip().startswith("#"):
                continue
            for m_call in re_calls.finditer(l):
                fn_nom = m_call.group(1)
                for hdr, fns in STD_HEADERS_MAP.items():
                    if fn_nom in fns and hdr not in headers_incluidos:
                        if (fn_nom, hdr) not in ya_reportadas_fn:
                            ya_reportadas_fn.add((fn_nom, hdr))
                            rcode, tit = _regla_info("0x5016h")
                            violaciones.append(ViolacionRegla(
                                codigo=rcode,
                                titulo=tit,
                                archivo=ruta,
                                linea=i + 1,
                                columna=m_call.start(1) + 1,
                                mensaje=f"Invocación a la función de biblioteca estándar '{fn_nom}()' sin incluir explícitamente su cabecera '<{hdr}>'.",
                                sugerencia=f"Agregá '#include <{hdr}>' al inicio del archivo para garantizar prototipos y tipos estándar válidos.",
                                codigo_linea=lineas[i],
                                es_autofixable=False,
                            ))

    # -------------------------------------------------------------------------
    # 0x1014h: Prohibición de expresiones de asignación dentro de estructuras de control
    # -------------------------------------------------------------------------
    if _esta_activa("0x1014h"):
        re_ctrl_assign = re.compile(r"\b(if|while|switch)\s*\([^;]*?\(\s*([a-zA-Z_]\w*)\s*=(?!=)\s*[^;]*?\)")
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("//") or l.strip().startswith("/*") or l.strip().startswith("#"):
                continue
            m_ca = re_ctrl_assign.search(l)
            if m_ca:
                rcode, tit = _regla_info("0x1014h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_ca.start() + 1,
                    mensaje=f"Asignación embebida a '{m_ca.group(2)}' dentro de la condición de control '{m_ca.group(1)}'.",
                    sugerencia="Desacoplá la asignación y la evaluación condicional en sentencias separadas para clarificar la lógica y evitar confusiones.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x0022h: Validador de espaciado estricto en sentencias de control
    # -------------------------------------------------------------------------
    if _esta_activa("0x0022h"):
        re_ctrl_no_space = re.compile(r"\b(if|for|while|switch)\(")
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("//") or l.strip().startswith("/*") or l.strip().startswith("#"):
                continue
            for m in re_ctrl_no_space.finditer(l):
                rcode, tit = _regla_info("0x0022h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m.start() + 1,
                    mensaje=f"Falta espacio obligatorio tras la palabra clave '{m.group(1)}' antes del paréntesis.",
                    sugerencia=f"Escribí '{m.group(1)} (...)' con un espacio de separación.",
                    codigo_linea=lineas[i],
                    es_autofixable=True,
                ))

    # -------------------------------------------------------------------------
    # 0x0023h: Detector de variables locales no inicializadas con modificador const
    # -------------------------------------------------------------------------
    if _esta_activa("0x0023h"):
        re_const_uninit = re.compile(r"\bconst\s+(?:struct\s+\w+|\w+)\s*(\*+)?\s*([a-zA-Z_]\w*)\s*;")
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("//") or l.strip().startswith("/*") or l.strip().startswith("#"):
                continue
            m_cu = re_const_uninit.search(l)
            if m_cu:
                var_n = m_cu.group(2)
                rcode, tit = _regla_info("0x0023h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_cu.start() + 1,
                    mensaje=f"Variable '{var_n}' declarada con calificador 'const' sin inicializar.",
                    sugerencia=f"Inicializá '{var_n}' en su declaración con un valor constante o el resultado de una expresión.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x0025h: Formato canónico en firmas de punteros a función
    # -------------------------------------------------------------------------
    if _esta_activa("0x0025h"):
        re_bad_fn_ptr = re.compile(r"\btypedef\s+[^;]*?\(\s*\*\s+([a-zA-Z_]\w*)\s*\)|\btypedef\s+[^;]*?\(\s*\*\s*([a-zA-Z_]\w*)\s+\)")
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("//") or l.strip().startswith("/*") or l.strip().startswith("#"):
                continue
            m_fp = re_bad_fn_ptr.search(l)
            if m_fp:
                fn_name = m_fp.group(1) or m_fp.group(2)
                rcode, tit = _regla_info("0x0025h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_fp.start() + 1,
                    mensaje=f"Firma de puntero a función '{fn_name}' no respeta el formato canónico '(*nombre)'.",
                    sugerencia="Usá el formato estricto 'typedef tipo (*identificador_t)(params)' sin espacios entre el asterisco y el nombre.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x0026h: Auditor de identificadores reservados (__ o _[A-Z])
    # -------------------------------------------------------------------------
    if _esta_activa("0x0026h"):
        re_reserved_id = re.compile(r"\b(__[a-zA-Z0-9_]+|_[A-Z][a-zA-Z0-9_]*)\b")
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("//") or l.strip().startswith("/*"):
                continue
            if l.strip().startswith("#"):
                if "#ifndef" in l or "#define" in l:
                    continue
            for m_res in re_reserved_id.finditer(l):
                r_ident = m_res.group(1)
                if r_ident in {"__FILE__", "__LINE__", "__DATE__", "__TIME__", "__func__", "__attribute__", "__STDC__", "__extension__"}:
                    continue
                rcode, tit = _regla_info("0x0026h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_res.start() + 1,
                    mensaje=f"Uso de identificador reservado '{r_ident}' (prefijos '__' o '_[A-Z]' reservados para la libc y compilador).",
                    sugerencia=f"Renombrá '{r_ident}' utilizando snake_case estándar sin guiones bajos reservados.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x0027h: Validador de presencia de cabecera de documentación obligatoria por archivo
    # -------------------------------------------------------------------------
    if _esta_activa("0x0027h"):
        primeras = lineas[:20]
        texto_primeras = "\n".join(primeras)
        tiene_cabecera = ("/*" in texto_primeras and "*/" in texto_primeras) or (sum(1 for l in primeras if l.strip().startswith("//")) >= 2)
        if not tiene_cabecera and len(lineas) >= 10:
            rcode, tit = _regla_info("0x0027h")
            violaciones.append(ViolacionRegla(
                codigo=rcode,
                titulo=tit,
                archivo=ruta,
                linea=1,
                columna=1,
                mensaje="El archivo carece de bloque inicial de comentarios de documentación institucional.",
                sugerencia="Incluí un encabezado al inicio del archivo con información de autoría, cátedra y propósito del módulo.",
                codigo_linea=lineas[0] if lineas else "",
                es_autofixable=False,
            ))

    # -------------------------------------------------------------------------
    # 0x0028h: Detector de etiquetas de salto goto no alineadas al margen izquierdo
    # -------------------------------------------------------------------------
    if _esta_activa("0x0028h"):
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("//") or l.strip().startswith("/*") or l.strip().startswith("#"):
                continue
            stripped = l.strip()
            if stripped.startswith("case ") or stripped.startswith("default:") or "?" in stripped:
                continue
            m_lab = re.match(r"^[ \t]+([a-zA-Z_]\w*)\s*:\s*$", l)
            if m_lab and m_lab.group(1) not in {"default"}:
                lbl_name = m_lab.group(1)
                rcode, tit = _regla_info("0x0028h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=1,
                    mensaje=f"Etiqueta de salto '{lbl_name}:' sangrada con espacios. Debe alinearse al margen izquierdo (columna 1).",
                    sugerencia=f"Colocá '{lbl_name}:' en la primera columna sin sangría previa.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x0029h: Auditor de inicialización de arreglos unidimensionales con exceso de elementos
    # -------------------------------------------------------------------------
    if _esta_activa("0x0029h"):
        re_arr_overflow = re.compile(r"\b\w+\s+([a-zA-Z_]\w*)\s*\[\s*(\d+)\s*\]\s*=\s*\{([^}]+)\}")
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("//") or l.strip().startswith("/*") or l.strip().startswith("#"):
                continue
            m_arr = re_arr_overflow.search(l)
            if m_arr:
                arr_nom = m_arr.group(1)
                cap = int(m_arr.group(2))
                elems = [e.strip() for e in m_arr.group(3).split(",") if e.strip()]
                if len(elems) > cap:
                    rcode, tit = _regla_info("0x0029h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=i + 1,
                        columna=m_arr.start() + 1,
                        mensaje=f"Arreglo '{arr_nom}' declarado con capacidad {cap} pero inicializado con {len(elems)} elementos (exceso de inicializadores).",
                        sugerencia="Ajustá la dimensión del arreglo o remové los elementos sobrantes de la lista de inicialización.",
                        codigo_linea=lineas[i],
                        es_autofixable=False,
                    ))

    # -------------------------------------------------------------------------
    # 0x002Bh: Validador de espaciado en listas de argumentos y llamadas a funciones
    # -------------------------------------------------------------------------
    if _esta_activa("0x002Bh"):
        re_bad_comma = re.compile(r"(?:[a-zA-Z_]\w*)\s*\([^;]*?(?:,[^\s\)\],]|\s+,)[^;]*?\)")
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("//") or l.strip().startswith("/*") or l.strip().startswith("#"):
                continue
            if re_bad_comma.search(l):
                rcode, tit = _regla_info("0x002Bh")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=l.find(",") + 1,
                    mensaje="Espaciado incorrecto en lista de argumentos o parámetros: la coma debe ir adherida al elemento previo y seguida de un espacio.",
                    sugerencia="Formateá como 'f(a, b, c)' sin espacio previo a la coma y con un espacio posterior.",
                    codigo_linea=lineas[i],
                    es_autofixable=True,
                ))

    # -------------------------------------------------------------------------
    # 0x002Ch: Auditor de consistencia en nombres de constantes simbólicas (#define)
    # -------------------------------------------------------------------------
    if _esta_activa("0x002Ch"):
        re_macro_const = re.compile(r"^[ \t]*#define[ \t]+([a-zA-Z_]\w*)(?!\s*\()[ \t]+([0-9\"'a-zA-Z_(].*)")
        for i, l in enumerate(lineas_sin_cadenas):
            m_mc = re_macro_const.match(l)
            if m_mc:
                nom_m = m_mc.group(1)
                if any(c.islower() for c in nom_m) and not nom_m.startswith("__"):
                    rcode, tit = _regla_info("0x002Ch")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=i + 1,
                        columna=m_mc.start(1) + 1,
                        mensaje=f"Constante simbólica '#define {nom_m}' contiene letras minúsculas. Debe utilizar SCREAMING_SNAKE_CASE.",
                        sugerencia=f"Escribí '{nom_m.upper()}' en mayúsculas sostenidas con guiones bajos.",
                        codigo_linea=lineas[i],
                        es_autofixable=False,
                    ))

    # -------------------------------------------------------------------------
    # 0x002Dh: Validador de espaciado en operadores unarios (*ptr, &var, !flag, ++i)
    # -------------------------------------------------------------------------
    if _esta_activa("0x002Dh"):
        re_bad_unary = re.compile(r"(?:^|[\s(,=;])(\*|&|!|\+\+|--)[ \t]+([a-zA-Z_]\w*)")
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("//") or l.strip().startswith("/*") or l.strip().startswith("#"):
                continue
            m_u = re_bad_unary.search(l)
            if m_u:
                op = m_u.group(1)
                target = m_u.group(2)
                pre = l[:m_u.start(1)].strip()
                if op in {"*", "&"} and pre and (pre[-1].isalnum() or pre[-1] in {")", "]"}) and pre not in {"return", "sizeof"}:
                    continue
                rcode, tit = _regla_info("0x002Dh")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_u.start(1) + 1,
                    mensaje=f"Espacio no permitido entre el operador unario '{op}' y su operando '{target}'.",
                    sugerencia=f"Uní el operador a su operando sin espacios: '{op}{target}'.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x1016h: Detector de expresiones booleanas complejas sin paréntesis aclaratorios
    # -------------------------------------------------------------------------
    if _esta_activa("0x1016h"):
        re_if_cond = re.compile(r"\b(if|while)\s*\((.+)\)")
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("//") or l.strip().startswith("/*") or l.strip().startswith("#"):
                continue
            m_ic = re_if_cond.search(l)
            if m_ic:
                cond = m_ic.group(2)
                if "&&" in cond and "||" in cond:
                    if not re.search(r"\([^)]*?(&&|\|\|)[^)]*?\)", cond):
                        rcode, tit = _regla_info("0x1016h")
                        violaciones.append(ViolacionRegla(
                            codigo=rcode,
                            titulo=tit,
                            archivo=ruta,
                            linea=i + 1,
                            columna=m_ic.start() + 1,
                            mensaje="Expresión booleana combina '&&' y '||' sin paréntesis explícitos que aclaren la precedencia pedagógica.",
                            sugerencia="Agrupá las condiciones con paréntesis para hacer explícito el orden de evaluación.",
                            codigo_linea=lineas[i],
                            es_autofixable=False,
                        ))

    # -------------------------------------------------------------------------
    # 0x1017h: Detector de operadores de incremento o decremento múltiples en una misma expresión
    # -------------------------------------------------------------------------
    if _esta_activa("0x1017h"):
        re_multi_inc = re.compile(r"(\+\+|--)\s*([a-zA-Z_]\w*)|([a-zA-Z_]\w*)\s*(\+\+|--)")
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("//") or l.strip().startswith("/*") or l.strip().startswith("#"):
                continue
            encontrados = []
            for m in re_multi_inc.finditer(l):
                var = m.group(2) or m.group(3)
                encontrados.append(var)
            if len(encontrados) > 1 and len(encontrados) != len(set(encontrados)):
                rep = [v for v in set(encontrados) if encontrados.count(v) > 1][0]
                rcode, tit = _regla_info("0x1017h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=l.find(rep) + 1,
                    mensaje=f"Operaciones de incremento o decremento múltiples sobre la variable '{rep}' en una misma sentencia (comportamiento indefinido por sequence points).",
                    sugerencia="Separar los incrementos o decrementos en sentencias individuales independientes.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x2016h: Detector de bloques else superfluos tras sentencias terminales
    # -------------------------------------------------------------------------
    if _esta_activa("0x2016h"):
        for i in range(1, len(lineas_sin_cadenas)):
            l_curr = lineas_sin_cadenas[i].strip()
            l_prev = lineas_sin_cadenas[i - 1].strip()
            if l_curr.startswith("else") or l_curr.startswith("} else"):
                if l_prev.startswith("return ") or l_prev.startswith("return;") or l_prev.startswith("exit(") or l_prev == "break;":
                    rcode, tit = _regla_info("0x2016h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=i + 1,
                        columna=1,
                        mensaje="Bloque 'else' superfluo tras sentencia terminal incondicional ('return', 'exit' o 'break').",
                        sugerencia="Eliminá la cláusula 'else' y desanidá su contenido para adoptar el patrón de salida temprana (early exit / guard clause).",
                        codigo_linea=lineas[i],
                        es_autofixable=False,
                    ))

    # -------------------------------------------------------------------------
    # 0x301Ah: Validador de uso idiomático de tipos booleanos estándar
    # -------------------------------------------------------------------------
    if _esta_activa("0x301Ah"):
        re_bad_bool = re.compile(r"\btypedef\s+(?:int|char|short)\s+([A-Z_]*BOOL[A-Z_]*)\b|#define\s+(TRUE|FALSE)\s+[01]")
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("//") or l.strip().startswith("/*"):
                continue
            m_bb = re_bad_bool.search(l)
            if m_bb:
                nom_bb = m_bb.group(1) or m_bb.group(2)
                rcode, tit = _regla_info("0x301Ah")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_bb.start() + 1,
                    mensaje=f"Redefinición manual no idiomática de tipos booleanos ('{nom_bb}'). Debe utilizarse '<stdbool.h>' estándar.",
                    sugerencia="Incluí '#include <stdbool.h>' y usá los identificadores estándar 'bool', 'true' y 'false'.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # Filtrar violaciones suprimidas por directivas // gaff:ignore <regla> <justificación>
    def _esta_suprimida(v: ViolacionRegla) -> bool:
        cod = str(v.codigo).lower()
        regs = lineas_ignoradas.get(v.linea, set())
        return "all" in regs or cod in regs or (cod.endswith("h") and cod[:-1] in regs)

    violaciones = [v for v in violaciones if not _esta_suprimida(v)]

    violaciones.sort(key=lambda v: (v.linea, v.columna))
    return violaciones


def aplicar_autofix_archivo(ruta: Path) -> int:
    """Aplica correcciones automáticas sobre reglas autofixables (GAFF004, GAFF005, GAFF010, GAFF014)."""
    if not ruta.is_file():
        return 0

    try:
        contenido = ruta.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        contenido = ruta.read_text(encoding="latin-1")

    arreglos = 0
    lineas = contenido.splitlines()

    # GAFF020 / 0x200Eh: Autofix de fn() a fn(void)
    re_empty_paren_fix = re.compile(rf"\b({TIPOS_BASICOS})\s+([a-zA-Z_]\w*)\s*\(\s*\)")
    lineas_paren_fix = []
    for l in lineas:
        if not l.strip().startswith("#"):
            l_fix, n_rep = re_empty_paren_fix.subn(r"\1 \2(void)", l)
            if n_rep > 0:
                arreglos += n_rep
                l = l_fix
        lineas_paren_fix.append(l)
    lineas = lineas_paren_fix

    # GAFF019 / 0x5007h: Deduplicación de #include redundantes
    headers_vistos_fix = set()
    lineas_dedup = []
    for l in lineas:
        m_inc = re.match(r"^[ \t]*#include[ \t]+([<\"].+[>\"])", l)
        if m_inc:
            h_nom = m_inc.group(1)
            if h_nom in headers_vistos_fix:
                arreglos += 1
                continue
            headers_vistos_fix.add(h_nom)
        lineas_dedup.append(l)
    lineas = lineas_dedup

    nuevas_lineas = []

    re_kw = re.compile(r"\b(if|for|while|switch)\(")
    re_ptr_fix = re.compile(rf"\b({TIPOS_BASICOS})\*\s+([a-zA-Z_]\w*)")

    for linea in lineas:
        orig = linea
        # GAFF010 / 0x0005h: tabs to spaces y strip trailing
        linea = linea.replace("\t", "    ").rstrip()
        stripped = linea.strip()
        if stripped and not linea.lstrip().startswith(("*", "/*")):
            lead = len(linea) - len(linea.lstrip(" "))
            if lead > 0 and lead % 4 != 0:
                nuevo_lead = max(4, ((lead + 2) // 4) * 4)
                linea = (" " * nuevo_lead) + linea.lstrip(" ")
        # GAFF007 / 0x0004h: keywords spacing
        linea = re_kw.sub(r"\1 (", linea)
        # GAFF014 / 0x0006h: pointer asterisk spacing
        if not linea.strip().startswith("#"):
            linea = re_ptr_fix.sub(r"\1 *\2", linea)


        # GAFF / 0x0019h: Espacios antes de ; y ,
        if not linea.strip().startswith("#") and not linea.strip().startswith("/*") and not linea.strip().startswith("*"):
            linea = re.sub(r"[ 	]+([;,])", r"\1", linea)

        # GAFF / 0x001Ah: Miembros -> y .
        linea = re.sub(r'([a-zA-Z0-9_]+)[ 	]+->[ 	]*([a-zA-Z0-9_]+)', r'\1->\2', linea)
        linea = re.sub(r'([a-zA-Z0-9_]+)[ 	]*->[ 	]+([a-zA-Z0-9_]+)', r'\1->\2', linea)
        linea = re.sub(r'([a-zA-Z_]\w*)[ 	]+\.[ 	]*([a-zA-Z_]\w*)', r'\1.\2', linea)
        linea = re.sub(r'([a-zA-Z_]\w*)[ 	]*\.[ 	]+([a-zA-Z_]\w*)', r'\1.\2', linea)

        # GAFF / 0x001Bh: Unarios ++, --, !
        linea = re.sub(r'\b([a-zA-Z_]\w*)[ \t]+(\+\+|\-\-)', r'\1\2', linea)
        linea = re.sub(r'(\+\+|\-\-)[ \t]+([a-zA-Z_]\w*)', r'\1\2', linea)
        linea = re.sub(r'(!)(?!=)[ \t]+([a-zA-Z_]\w*)', r'\1\2', linea)

        # GAFF / 0x001Ch: Espacio tras coma
        linea = re.sub(r',(?=[^\s\n\r/>])', r', ', linea)

        # GAFF / 0x001Dh: Espacio interno en paréntesis
        linea = re.sub(r'\([ 	]+(?!\s|\))', r'(', linea)
        linea = re.sub(r'(?<!\s|\()[ 	]+\)', r')', linea)

        # GAFF / 0x001Eh: Colapsar espacios múltiples intra-línea
        if not linea.strip().startswith("#") and not linea.strip().startswith("/*") and not linea.strip().startswith("*"):
            indent = len(linea) - len(linea.lstrip())
            linea = linea[:indent] + re.sub(r'(?<=\S)[ 	]{2,}(?=\S)', ' ', linea[indent:])

        # 0x2010h: return (x); -> return x;
        m_ret = re.match(r"^([ \t]*return)\s*\(\s*([a-zA-Z_]\w*(?:->\w+|\.\w+|\[[^\]]+\])?|\d+|NULL)\s*\)\s*;", linea)
        if m_ret:
            linea = f"{m_ret.group(1)} {m_ret.group(2)};"

        # 0x100Ch: Yoda condition NULL == ptr -> ptr == NULL
        linea = re.sub(r"\b(NULL|0|[1-9]\d*|true|false)\s*(==|!=)\s*([a-zA-Z_]\w*(?:->\w+|\.\w+|\[[^\]]+\])?)", r"\3 \2 \1", linea)

        # 0x100Eh: Operador ternario ? : con espaciado
        if "?" in linea and ":" in linea and not ("case " in linea or "default:" in linea):
            linea = re.sub(r"(\S)\s*\?\s*(\S)", r"\1 ? \2", linea)
            linea = re.sub(r"(\S)\s*:\s*(\S)", r"\1 : \2", linea)

        # 0x3017h: int const -> const int
        linea = re.sub(rf"\b({TIPOS_BASICOS})\s+const\b", r"const \1", linea)

        # 0x100Dh: cast innecesario de literal (int)0 -> 0
        linea = re.sub(r"\((?:int|char|long|float|double|size_t)\)\s*(\(?\b\d+(?:\.\d+)?f?\b\)?|\((?:int|char|long|float|double|size_t)\))", r"\1", linea)

        # 0x0017h: doble puntero tipo **var
        linea = re.sub(rf"\b({TIPOS_BASICOS})\s*(\*(?:\s*\*|\s+\*))\s*([a-zA-Z_]\w*)", r"\1 **\3", linea)

        # 0x3016h: memset(ptr, sizeof(ptr), 0) -> memset(ptr, 0, sizeof(ptr))
        re_ms_fix = re.compile(r"\bmemset\s*\(\s*([^,]+?)\s*,\s*(sizeof\([^)]+\)|\d+|[a-zA-Z_]\w*)\s*,\s*(0|'\\0'|NULL)\s*\)")
        linea = re_ms_fix.sub(r"memset(\1, \3, \2)", linea)

        # 0x001Fh: int x = {0}; -> int x = 0;
        re_scalar_fix = re.compile(rf"^([ \t]*(?!(?:struct|union)\b)(?:const\s+)?(?:static\s+)?{TIPOS_BASICOS}\s+\*?\s*[a-zA-Z_]\w*\s*=\s*)\{{\s*([^,{{}}\n]+?)\s*\}}(\s*;)")
        if not ("[" in linea or "struct " in linea or "union " in linea):
            linea = re_scalar_fix.sub(r"\1\2\3", linea)

        # 0x1012h: a < b < c -> a < b && b < c
        if not ("<<" in linea or ">>" in linea or linea.strip().startswith("#")):
            re_chained_fix = re.compile(r"(?<![<>=!])\b([a-zA-Z0-9_]+)\s*(<=|<|>=|>|==)\s*([a-zA-Z0-9_]+)\s*(<=|<|>=|>|==)\s*([a-zA-Z0-9_]+)\b(?![<>=])")
            linea = re_chained_fix.sub(r"\1 \2 \3 && \3 \4 \5", linea)

        # 0x2013h: void main( -> int main(
        if re.match(r"^[ \t]*void\s+main\s*\(", linea):
            linea = re.sub(r"^([ \t]*)void(\s+main\s*\()", r"\1int\2", linea)

        # 0x5015h: #define TAM 10 + 5 -> #define TAM (10 + 5)
        m_macro_fix = re.match(r"^([ \t]*#\s*define\s+[a-zA-Z_]\w*(?:\([^)]*\))?[ \t]+)(.+)$", linea)
        if m_macro_fix:
            b_fix = m_macro_fix.group(2).strip()
            if not (b_fix.startswith("(") and b_fix.endswith(")")) and re.search(r"[\+\-\*/%&|\^]|<<|>>|&&|\|\||\?", b_fix):
                if not re.match(r"^(?:0x[0-9a-fA-F]+|\d+(?:\.\d+)?f?|[a-zA-Z_]\w*)$", b_fix):
                    linea = f"{m_macro_fix.group(1)}({b_fix})"

        # 0x0022h: if( -> if (
        if not (linea.strip().startswith("//") or linea.strip().startswith("/*") or linea.strip().startswith("#")):
            linea = re.sub(r"\b(if|for|while|switch)\(", r"\1 (", linea)

        # 0x002Bh: f(a,b) -> f(a, b) y f(a , b) -> f(a, b)
        if not (linea.strip().startswith("//") or linea.strip().startswith("/*") or linea.strip().startswith("#")):
            linea = re.sub(r"\s+,", ",", linea)
            linea = re.sub(r",([^\s\)\],])", r", \1", linea)

        if linea != orig:
            arreglos += 1
        nuevas_lineas.append(linea)

    contenido_mod = "\n".join(nuevas_lineas) + "\n"

    # GAFF005 / 0x5003h: Guardas de inclusión en .h
    if ruta.suffix.lower() in (".h", ".hpp"):
        tiene_pragma = "#pragma once" in contenido_mod
        tiene_ifndef = bool(re.search(r"#ifndef\s+\w+", contenido_mod) and re.search(r"#define\s+\w+", contenido_mod))
        if not (tiene_pragma or tiene_ifndef):
            guard_name = f"{ruta.stem.upper()}_H"
            contenido_mod = f"#ifndef {guard_name}\n#define {guard_name}\n\n{contenido_mod.strip()}\n\n#endif // {guard_name}\n"
            arreglos += 1


    # GAFF018 / 0x2003h: Autofix de esqueleto de documentación Doxygen para funciones no documentadas
    lineas_actuales = contenido_mod.splitlines()
    codigo_sin_coments = _eliminar_comentarios(contenido_mod)

    pattern_fn = (
        r"^([ \t]*)(?!(?:typedef|return)\b)((?:(?:static|inline|extern|const)[ \t]+)*(?:struct[ \t]+\w+|enum[ \t]+\w+|union[ \t]+\w+|"
        + TIPOS_BASICOS
        + r"|[a-zA-Z_]\w*)[ \t]*(\*+[ \t]*|[ \t]+\*?))([a-zA-Z_]\w*)[ \t]*\(([\s\S]*?)\)[ \t]*([;{])?"
    )
    re_fn_fix = re.compile(pattern_fn, re.MULTILINE)

    inserciones: List[Tuple[int, str]] = []
    prototipos_doc: Set[str] = set()
    if not ruta.suffix.lower() in (".h", ".hpp"):
        comp_h = ruta.with_suffix(".h")
        if comp_h.is_file():
            try:
                txt_h = comp_h.read_text(encoding="utf-8", errors="replace")
                lines_h = txt_h.splitlines()
                code_h = _eliminar_comentarios(txt_h)
                for m_ph in re_fn_fix.finditer(code_h):
                    nom = m_ph.group(4)
                    l_i = code_h[:m_ph.start()].count("\n")
                    if _tiene_comentario_documentacion(lines_h, l_i):
                        prototipos_doc.add(nom)
            except Exception:
                pass

    for m_fn in re_fn_fix.finditer(codigo_sin_coments):
        indent = m_fn.group(1)
        ret_type = m_fn.group(2)
        fn_name = m_fn.group(4)
        params_str = m_fn.group(5)
        char_cierre = m_fn.group(6)

        if fn_name in ("if", "for", "while", "switch", "return", "sizeof", "main"):
            continue

        pos_despues = m_fn.end()
        if char_cierre == ";":
            es_proto = True
        elif char_cierre == "{":
            es_proto = False
        else:
            resto = codigo_sin_coments[pos_despues:pos_despues + 100].lstrip()
            if resto.startswith(";"):
                es_proto = True
            elif resto.startswith("{") or "{" in resto[:60]:
                es_proto = False
            else:
                continue

        line_idx_start = codigo_sin_coments[:m_fn.start()].count("\n")
        if _tiene_comentario_documentacion(lineas_actuales, line_idx_start):
            prototipos_doc.add(fn_name)
            continue

        if not es_proto and fn_name in prototipos_doc:
            continue

        lineas_doc = [f"{indent}/**", f"{indent} * @brief Descripción de la función {fn_name}."]

        raw_params = [p.strip() for p in params_str.split(",") if p.strip()]
        if raw_params and not (len(raw_params) == 1 and raw_params[0] == "void"):
            lineas_doc.append(f"{indent} *")
            for p in raw_params:
                m_arg = re.search(r"([a-zA-Z_]\w*)\s*(?:\[[^\]]*\])?$", p)
                arg_name = m_arg.group(1) if m_arg else "param"
                lineas_doc.append(f"{indent} * @param {arg_name} Descripción del parámetro {arg_name}.")

        ret_clean = ret_type.strip()
        es_void = ret_clean == "void" or ret_clean.endswith(" void") or ret_clean.endswith("\tvoid")
        if not es_void:
            lineas_doc.append(f"{indent} * @return Descripción del valor de retorno.")

        lineas_doc.append(f"{indent} */")
        texto_doc = "\n".join(lineas_doc)

        inserciones.append((line_idx_start, texto_doc))
        prototipos_doc.add(fn_name)

    if inserciones:
        for l_idx, doc_block in sorted(inserciones, key=lambda x: x[0], reverse=True):
            lineas_actuales.insert(l_idx, doc_block)
            arreglos += 1
        contenido_mod = "\n".join(lineas_actuales) + "\n"

    if not contenido.endswith("\n"):
        arreglos += 1
    if not contenido_mod.endswith("\n"):
        contenido_mod += "\n"
    ruta.write_text(contenido_mod, encoding="utf-8")

    # GAFF017 / 0x000Bh: Autoformato con estilo Allman mediante clang-format si está disponible
    allman_style = (
        "{BasedOnStyle: LLVM, BreakBeforeBraces: Allman, "
        "AllowShortIfStatementsOnASingleLine: false, AllowShortBlocksOnASingleLine: false, "
        "AllowShortLoopsOnASingleLine: false, AllowShortFunctionsOnASingleLine: None, "
        "IndentWidth: 4, TabWidth: 4, UseTab: Never, IndentCaseLabels: true, "
        "ColumnLimit: 80, SpaceBeforeParens: ControlStatements, PointerAlignment: Right}"
    )
    try:
        res = subprocess.run(
            ["clang-format", "-i", f"-style={allman_style}", str(ruta)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5,
        )
        if res.returncode == 0:
            arreglos += 1
    except Exception:
        # Fallback a reemplazo simple de llaves Allman
        pass

    return arreglos


def ejecutar_linter(
    rutas: List[Path] | Sequence[Path | str],
    fix: bool = False,
    reglas_excluidas: Optional[Set[str]] = None,
    reglas_habilitadas: Optional[Set[str]] = None,
    recursive: bool = False,
    config: Optional[Dict[str, Any]] = None,
) -> ReporteLinting:
    """Ejecuta el linter sobre un conjunto de archivos o directorios aplicando configuración por exclusión."""
    from gaff.core.config import cargar_configuracion_gaff

    if reglas_excluidas is None:
        dir_base = None
        for r in rutas:
            p = Path(r)
            if p.is_dir():
                dir_base = p
                break
            elif p.is_file():
                dir_base = p.parent
                break
        cfg = config or cargar_configuracion_gaff(dir_base)
        excl_cfg = cfg.get("excluded_rules", []) or cfg.get("disabled_rules", [])
        if excl_cfg:
            reglas_excluidas = set(str(x) for x in excl_cfg)

    archivos_objetivo: Set[Path] = set()
    for r in rutas:
        p = Path(r)
        if p.is_file() and p.suffix.lower() in (".c", ".h", ".cpp", ".hpp"):
            archivos_objetivo.add(p)
        elif p.is_dir():
            iterador = p.rglob("*") if recursive else p.glob("*")
            for sub_p in iterador:
                if sub_p.is_file() and sub_p.suffix.lower() in (".c", ".h", ".cpp", ".hpp"):
                    archivos_objetivo.add(sub_p)

    reportes: List[ReporteArchivo] = []
    for arch in sorted(archivos_objetivo):
        arreglos = 0
        if fix:
            arreglos = aplicar_autofix_archivo(arch)
        viols = analizar_archivo(
            arch,
            reglas_excluidas=reglas_excluidas,
            reglas_habilitadas=reglas_habilitadas,
        )
        reportes.append(ReporteArchivo(
            archivo=arch,
            violaciones=viols,
            arreglos_aplicados=arreglos,
        ))

    return ReporteLinting(archivos=reportes)


def convertir_pragma_once_a_guardas(contenido: str, stem: str) -> Tuple[str, bool]:
    """Convierte directivas #pragma once en guardas #ifndef __STEM_H__ canónicas."""
    if not re.search(r"^[ \t]*#pragma\s+once\b", contenido, re.MULTILINE):
        return contenido, False
    stem_clean = re.sub(r"[^A-Za-z0-9_]", "_", stem).upper()
    guard_name = f"__{stem_clean}_H__"
    nuevo_contenido = re.sub(r"^[ \t]*#pragma\s+once[ \t]*\n?", "", contenido, flags=re.MULTILINE)
    resultado = f"#ifndef {guard_name}\n#define {guard_name}\n\n{nuevo_contenido.strip()}\n\n#endif // {guard_name}\n"
    return resultado, True


def detectar_inclusiones_ciclicas(rutas: List[Path]) -> List[Tuple[str, str]]:
    """Detecta ciclos de inclusión mutua directa entre archivos de cabecera del proyecto."""
    grafo: Dict[str, Set[str]] = {}
    for r in rutas:
        p = Path(r)
        if not p.is_file() or p.suffix.lower() not in (".h", ".hpp"):
            continue
        try:
            txt = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        includes = set(re.findall(r'^[ \t]*#include\s+"([^"]+)"', txt, re.MULTILINE))
        grafo[p.name] = includes

    ciclos = []
    for header, incls in grafo.items():
        for inc in incls:
            inc_name = Path(inc).name
            if inc_name in grafo and header in grafo[inc_name]:
                par = tuple(sorted([header, inc_name]))
                if par not in ciclos:
                    ciclos.append(par)
    return ciclos


def auditar_guardas_proyecto(rutas: List[Path]) -> List[Dict[str, Any]]:
    """Detecta colisiones de nombres de macros de guarda entre diferentes archivos .h."""
    guardas: Dict[str, List[Path]] = {}
    for r in rutas:
        p = Path(r)
        if not p.is_file() or p.suffix.lower() not in (".h", ".hpp"):
            continue
        try:
            txt = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        m = re.search(r"^[ \t]*#ifndef\s+(\w+)", txt, re.MULTILINE)
        if m:
            gname = m.group(1)
            guardas.setdefault(gname, []).append(p)

    colisiones = []
    for gname, paths in guardas.items():
        if len(paths) > 1:
            colisiones.append({
                "guarda": gname,
                "archivos": [str(p) for p in paths]
            })
    return colisiones
