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
    # -------------------------------------------------------------------------

    # 0x5003h: Guardas de inclusión en cabeceras (.h)
    if ctx.esta_activa("0x5003h") and es_header:
        tiene_pragma = bool(re.search(r"^[ \t]*#pragma\s+once\b", codigo_sin_comentarios, re.MULTILINE))
        m_guard = re.search(r"^[ \t]*#ifndef\s+(\w+)", codigo_sin_comentarios, re.MULTILINE)
        m_def = re.search(r"^[ \t]*#define\s+(\w+)", codigo_sin_comentarios, re.MULTILINE)
        tiene_ifndef = bool(m_guard and m_def)
        if not (tiene_pragma or tiene_ifndef):
            rcode, tit = ctx.regla_info("0x5003h")
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
                rcode, tit = ctx.regla_info("0x5003h")
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
            rcode, tit = ctx.regla_info("0x5003h")
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
    if ctx.esta_activa("0x5004h"):
        re_str_inseguro = re.compile(r"\b(strcpy|strcat|sprintf)\s*\(")
        for idx, linea in enumerate(lineas_sin_comentarios, 1):
            m = re_str_inseguro.search(linea)
            if m:
                fn = m.group(1)
                rcode, tit = ctx.regla_info("0x5004h")
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
    if ctx.esta_activa("0x5006h"):
        re_gets = re.compile(r"\bgets\s*\(")
        re_scanf_s = re.compile(r'\bscanf\s*\(\s*"[^"]*%s[^"]*"')
        for idx, linea in enumerate(lineas_sin_comentarios, 1):
            m_gets = re_gets.search(linea)
            if m_gets:
                rcode, tit = ctx.regla_info("0x5006h")
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
                rcode, tit = ctx.regla_info("0x5006h")
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
    if ctx.esta_activa("0x5001h") and not es_header:
        re_vla = re.compile(rf"^\s*{TIPOS_BASICOS}\s+\w+\s*\[\s*([a-zA-Z_]\w*)\s*\]\s*;", re.MULTILINE)
        for m in re_vla.finditer(codigo_sin_comentarios):
            var_name = m.group(1)
            # Si el tamaño es una variable con letras minúsculas (no constante en mayúsculas)
            if var_name != var_name.upper():
                line_no = codigo_sin_comentarios[:m.start()].count("\n") + 1
                rcode, tit = ctx.regla_info("0x5001h")
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
                rcode, tit = ctx.regla_info("0x5001h")
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
    # 0x2006h: Una aserción por cada función de prueba
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x8001h"):
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
                rcode, tit = ctx.regla_info("0x8001h")
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
    # 0x5002h: Desarrollá y compilá siempre con todas las advertencias (prohibido silenciar warnings)
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x5002h"):
        re_pragma_warn = re.compile(r"#pragma\s+(?:GCC\s+diagnostic\s+ignored|warning\s*\(\s*disable)", re.IGNORECASE)
        for i, l in enumerate(lineas):
            m_pw = re_pragma_warn.search(l)
            if m_pw:
                rcode, tit = ctx.regla_info("0x5002h")
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
    # 0x5007h: Inclusiones redundantes o duplicadas de la misma cabecera #include
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x5007h"):
        headers_vistos: Dict[str, int] = {}
        re_inc_line = re.compile(r"^[ \t]*#include[ \t]+([<\"].+[>\"])")
        for i, l in enumerate(lineas):
            m_inc = re_inc_line.match(l)
            if m_inc:
                h_name = m_inc.group(1)
                if h_name in headers_vistos:
                    rcode, tit = ctx.regla_info("0x5007h")
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
    if ctx.esta_activa("0x5008h"):
        re_unsafe_fn = re.compile(r"\b(gets|atoi)\s*\(")
        for i, l in enumerate(lineas_sin_comentarios):
            m_uf = re_unsafe_fn.search(l)
            if m_uf:
                bad_fn = m_uf.group(1)
                sug = "fgets(buf, sizeof(buf), stdin)" if bad_fn == "gets" else "strtol(str, &endptr, 10)"
                rcode, tit = ctx.regla_info("0x5008h")
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
    if ctx.esta_activa("0x5009h"):
        re_int_div_float = re.compile(r"\b(?:float|double)\s+[a-zA-Z_]\w*\s*=\s*(\d+)\s*/\s*(\d+)\s*;")
        for i, l in enumerate(lineas_sin_comentarios):
            m_idf = re_int_div_float.search(l)
            if m_idf:
                n1 = m_idf.group(1)
                n2 = m_idf.group(2)
                rcode, tit = ctx.regla_info("0x5009h")
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

    return violaciones
