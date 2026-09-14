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
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x200Dh"):
        re_empty_paren_fn = re.compile(rf"^[ \t]*(?!typedef|extern){TIPOS_BASICOS}\s+(\w+)\s*\(\s*\)\s*(?:\{{|;)", re.MULTILINE)
        for m_ep in re_empty_paren_fn.finditer(codigo_sin_comentarios):
            fn_name = m_ep.group(1)
            linea_num = contenido_original[:m_ep.start()].count("\n") + 1
            rcode, tit = ctx.regla_info("0x200Dh")
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
    if ctx.esta_activa("0x200Eh") and ruta.suffix.lower() == ".c":
        re_public_fn = re.compile(rf"^(?!static|typedef|extern)[ \t]*{TIPOS_BASICOS}\s+(\w+)\s*\([^)]*\)\s*\{{", re.MULTILINE)
        header_declaraciones = set()
        comp_h = ruta.with_suffix(".h")
        if comp_h.is_file():
            try:
                txt_h = comp_h.read_text(encoding="utf-8", errors="replace")
                header_declaraciones = set(re.findall(rf"\b{TIPOS_BASICOS}\s+(\w+)\s*\(", eliminar_comentarios(txt_h)))
            except Exception:
                pass
        for m_pf in re_public_fn.finditer(codigo_sin_comentarios):
            fn_name = m_pf.group(1)
            if fn_name in ("main", "if", "for", "while") or fn_name.startswith("test_"):
                continue
            if comp_h.is_file() and fn_name not in header_declaraciones:
                linea_num = contenido_original[:m_pf.start()].count("\n") + 1
                rcode, tit = ctx.regla_info("0x200Eh")
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
    # 0x2010h: Prohibición de sombreado de parámetros mediante variables locales con el mismo nombre
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x2010h"):
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
                    rcode, tit = ctx.regla_info("0x2010h")
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
    if ctx.esta_activa("0x2010h"):
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
                mut_matches = list(re.finditer(rf"\b{vp}\s*(?:\+\+|\-\-|\+=|\-=|=(?!=))", body_fn))
                for mm in mut_matches:
                    prefix_str = body_fn[:mm.start()].rstrip()
                    m_prev_word = re.search(r"\b(\w+)$", prefix_str)
                    if m_prev_word and m_prev_word.group(1) in ("int", "float", "char", "double", "void", "long", "short", "size_t", "bool"):
                        continue
                    linea_num = contenido_original[:m_fvp.start()].count("\n") + 1
                    rcode, tit = ctx.regla_info("0x2010h")
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
    # 0x200Eh: Comentarios de cierre en bloques extensos (> 25 líneas)
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x200Dh"):
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
                                rcode, tit = ctx.regla_info("0x200Dh")
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
    if ctx.esta_activa("0x200Eh"):
        re_empty_proto = re.compile(rf"\b({TIPOS_BASICOS})\s+([a-zA-Z_]\w*)\s*\(\s*\)\s*([;{{])")
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("#") or l.strip().startswith("*") or l.strip().startswith("//"):
                continue
            for m in re_empty_proto.finditer(l):
                tipo = m.group(1)
                nom = m.group(2)
                if nom in ("if", "for", "while", "switch", "return", "sizeof"):
                    continue
                rcode, tit = ctx.regla_info("0x200Eh")
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
    # 0x2010h: Prohibición de paréntesis superfluos en sentencia return
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x200Fh"):
        re_ret_paren = re.compile(r"^[ \t]*return\s*\(\s*([a-zA-Z_]\w*(?:->\w+|\.\w+|\[[^\]]+\])?|\d+|NULL)\s*\)\s*;")
        for i, l in enumerate(lineas_sin_cadenas):
            m = re_ret_paren.match(l)
            if m:
                val = m.group(1)
                rcode, tit = ctx.regla_info("0x200Fh")
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
    # 0x2013h: Tipo de retorno obligatorio 'int' en la función main()
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x2012h"):
        re_void_main = re.compile(r"^[ \t]*void\s+main\s*\(")
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("//") or l.strip().startswith("/*"):
                continue
            m_vm = re_void_main.search(l)
            if m_vm:
                rcode, tit = ctx.regla_info("0x2012h")
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
    # 0x2016h: Detector de bloques else superfluos tras sentencias terminales
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x2013h"):
        for i in range(1, len(lineas_sin_cadenas)):
            l_curr = lineas_sin_cadenas[i].strip()
            l_prev = lineas_sin_cadenas[i - 1].strip()
            if l_curr.startswith("else") or l_curr.startswith("} else"):
                if l_prev.startswith("return ") or l_prev.startswith("return;") or l_prev.startswith("exit(") or l_prev == "break;":
                    rcode, tit = ctx.regla_info("0x2013h")
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

    return violaciones
