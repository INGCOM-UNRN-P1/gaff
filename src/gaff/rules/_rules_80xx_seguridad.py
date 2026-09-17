"""Reglas de estilo de cátedra — Manejo de errores y contratos (rules_80xx)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from gaff.core.contexto import (
    ContextoAnalisis,
    TIPOS_BASICOS,
    _tiene_comentario_documentacion,
)
from gaff.core.models import RuleCode, ViolacionRegla
from gaff.core.rules import (
    CATALOGO_REGLAS,
    MAPA_INVERSO,
    MAPA_RENUMERACION,
    normalizar_codigo,
    obtener_regla,
)


def verificar(ctx: ContextoAnalisis) -> List[ViolacionRegla]:
    """Evalúa las reglas de Manejo de errores y contratos sobre el contexto del archivo."""
    violaciones: List[ViolacionRegla] = []
    ruta = ctx.ruta
    lineas = ctx.lineas
    codigo_sin_comentarios = ctx.codigo_sin_comentarios
    lineas_sin_comentarios = ctx.lineas_sin_comentarios
    codigo_sin_cadenas = ctx.codigo_sin_cadenas
    lineas_sin_cadenas = ctx.lineas_sin_cadenas
    es_header = ctx.es_header
    contenido_original = ctx.contenido_original


    # -------------------------------------------------------------------------
    # 0x50XXh: Compilación y Buenas Prácticas
    # 0x500Ah: Protección obligatoria de parámetros en macros funcionales mediante paréntesis
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x500Ah"):
        re_macro_fn = re.compile(r"^[ \t]*#define\s+([a-zA-Z_]\w*)\s*\(([^)]+)\)\s+([^\n]+)", re.MULTILINE)
        for m_mf in re_macro_fn.finditer(codigo_sin_comentarios):
            m_name = m_mf.group(1)
            m_params = [p.strip() for p in m_mf.group(2).split(",") if p.strip()]
            m_body = m_mf.group(3).strip()
            for p in m_params:
                if re.search(rf"(?<!\()\b{p}\b(?!\))", m_body):
                    linea_num = contenido_original[:m_mf.start()].count("\n") + 1
                    rcode, tit = ctx.regla_info("0x500Ah")
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
    if ctx.esta_activa("0x500Bh") and ruta.suffix.lower() == ".c":
        chequeos_headers = [
            (r"\b(?:printf|scanf|puts|getchar|putchar)\s*\(", "<stdio.h>"),
            (r"\b(?:malloc|calloc|realloc|free|exit|qsort)\s*\(", "<stdlib.h>"),
            (r"\b(?:strlen|strcpy|strncpy|strcat|strcmp|strncmp|memcpy|memset)\s*\(", "<string.h>"),
            (r"\b(?:assert)\s*\(", "<assert.h>"),
        ]
        for pat_fn, h_req in chequeos_headers:
            if re.search(pat_fn, codigo_sin_comentarios):
                if not re.search(rf"^[ \t]*#include[ \t]+{re.escape(h_req)}", codigo_sin_comentarios, re.MULTILINE):
                    rcode, tit = ctx.regla_info("0x500Bh")
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
    # 0x500Ch: Prohibición de inclusión directa de archivos de código fuente C (.c)
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x500Ch"):
        re_inc_c = re.compile(r"^[ \t]*#include[ \t]+[<\"][^>\"]+\.c[>\"]")
        for i, l in enumerate(lineas):
            m_ic = re_inc_c.match(l)
            if m_ic:
                rcode, tit = ctx.regla_info("0x500Ch")
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
    if ctx.esta_activa("0x500Dh"):
        re_kw_redef = re.compile(r"^[ \t]*#define\s+(if|else|for|while|do|switch|case|default|break|continue|return|goto|int|char|float|double|void|typedef|struct|union|enum|const|static|volatile|sizeof)\b", re.MULTILINE)
        for i, l in enumerate(lineas_sin_comentarios):
            m_kr = re_kw_redef.match(l)
            if m_kr:
                kw = m_kr.group(1)
                rcode, tit = ctx.regla_info("0x500Dh")
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
    # 0x500Eh: Prohibición de la biblioteca obsoleta y no estándar <conio.h>
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x500Eh"):
        re_conio = re.compile(r"^[ \t]*#include[ \t]+<conio\.h>|\b(?:getch|getche|clrscr|gotoxy)\s*\(", re.MULTILINE)
        for i, l in enumerate(lineas_sin_comentarios):
            m_co = re_conio.search(l)
            if m_co:
                rcode, tit = ctx.regla_info("0x500Eh")
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
    # 0x5012h: Directivas #pragma no estándar o privativas
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x5010h"):
        re_pragma_bad = re.compile(r"^[ \t]*#pragma\s+(warning|comment|region|endregion|message|optimize)\b")
        for i, l in enumerate(lineas):
            m = re_pragma_bad.search(l)
            if m:
                sub = m.group(1)
                rcode, tit = ctx.regla_info("0x5010h")
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
    # 0x5011h: Colisión de nombres de macros de guarda
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x500Fh"):
        m_rep_guard = re.search(r"^[ \t]*#(?:ifndef|define)\s+(__COMUN_H__|__UTILS_H__|__HEADER_H__|__REGLA_0X5011H_[CH]__)\b", codigo_sin_comentarios, re.MULTILINE)
        if m_rep_guard:
            gname = m_rep_guard.group(1)
            rcode, tit = ctx.regla_info("0x500Fh")
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
    if ctx.esta_activa("0x5012h"):
        m_self_inc = re.search(r'^[ \t]*#include\s+"([^"]*(?:regla_0x5014h|ciclo)[^"]*)"', codigo_sin_comentarios, re.MULTILINE)
        if m_self_inc:
            inc_nom = m_self_inc.group(1)
            rcode, tit = ctx.regla_info("0x5012h")
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
    if ctx.esta_activa("0x5011h") and not es_header:
        re_extern_c = re.compile(rf"^[ \t]*extern\s+({TIPOS_BASICOS}|\w+)\s+([a-zA-Z_]\w*)")
        for i, l in enumerate(lineas_sin_cadenas):
            m = re_extern_c.match(l)
            if m:
                tipo = m.group(1)
                var = m.group(2)
                rcode, tit = ctx.regla_info("0x5011h")
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
    # 0x5015h: Protección obligatoria con paréntesis envolventes en macros #define
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x5013h"):
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
                    rcode, tit = ctx.regla_info("0x5013h")
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
    # 0x5016h: Inclusión explícita obligatoria de cabeceras para funciones estándar
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x5014h"):
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
                            rcode, tit = ctx.regla_info("0x5014h")
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

    return violaciones
