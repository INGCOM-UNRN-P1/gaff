"""Reglas de estilo de cátedra — Funciones y modularización (rules_40xx)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from gaff.core.contexto import (
    ContextoAnalisis,
    TIPOS_BASICOS,
    _tiene_comentario_documentacion,
    eliminar_comentarios,
    enmascarar_literales,
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
    """Evalúa las reglas de Funciones y modularización sobre el contexto del archivo."""
    violaciones: List[ViolacionRegla] = []
    ruta = ctx.ruta
    lineas = ctx.lineas
    codigo_sin_comentarios = ctx.codigo_sin_comentarios
    lineas_sin_comentarios = ctx.lineas_sin_comentarios
    codigo_sin_cadenas = ctx.codigo_sin_cadenas
    lineas_sin_cadenas = ctx.lineas_sin_cadenas
    es_header = ctx.es_header
    contenido_original = ctx.contenido_original


    # 0x2005h: Longitud máxima de función (> 50 líneas)
    if ctx.esta_activa("0x2005h"):
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
                rcode, tit = ctx.regla_info("0x2005h")
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
    if ctx.esta_activa("0x2002h") and not es_header:
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
                rcode, tit = ctx.regla_info("0x2002h")
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

    # 0x2001h (GAFF025 / GAFF065): Anidación máxima de 3 niveles dentro de funciones
    if ctx.esta_activa("0x2001h"):
        codigo_nesting = enmascarar_literales(codigo_sin_comentarios)
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
                        rcode, tit = ctx.regla_info("0x2001h")
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

    # -------------------------------------------------------------------------
    # 0x2008h: Valores de retorno numéricos deben ser constantes o enums
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x2007h"):
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
                    rcode, tit = ctx.regla_info("0x2007h")
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
    if ctx.esta_activa("0x2008h") and ruta.suffix.lower() == ".c":
        re_main_block = re.compile(r"int\s+main\s*\([^)]*\)\s*\{", re.MULTILINE)
        m_main = re_main_block.search(codigo_sin_comentarios)
        if m_main:
            todas_fns = re.findall(rf"^(?!typedef|extern|static\s+const)\s*{TIPOS_BASICOS}\s+(\w+)\s*\([^;]*\)\s*\{{", codigo_sin_comentarios, re.MULTILINE)
            fns_auxiliares = [f for f in todas_fns if f != "main"]
            if not fns_auxiliares and len(lineas) > 35:
                linea_num = contenido_original[:m_main.start()].count("\n") + 1
                rcode, tit = ctx.regla_info("0x2008h")
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
    # 0x200Bh: Modularización: una función no debe exceder 4 parámetros de entrada
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x200Ah"):
        re_fn_params = re.compile(rf"^(?!typedef|extern)[ \t]*{TIPOS_BASICOS}\s+(\w+)\s*\(([^)]+)\)\s*(?:\{{|;)", re.MULTILINE)
        for m_fp in re_fn_params.finditer(codigo_sin_comentarios):
            fn_name = m_fp.group(1)
            params_raw = [p.strip() for p in m_fp.group(2).split(",") if p.strip()]
            if len(params_raw) > 4:
                linea_num = contenido_original[:m_fp.start()].count("\n") + 1
                rcode, tit = ctx.regla_info("0x200Ah")
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
    # 0x200Dh: Cada función debe tener a lo sumo un return
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x200Ch"):
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
                        rcode, tit = ctx.regla_info("0x200Ch")
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
    # 0x200Eh: Declaración explícita de (void) en funciones que no reciben parámetros

    return violaciones
