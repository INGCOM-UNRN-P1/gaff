"""Reglas de estilo de cátedra — Variables globales y locales (rules_30xx)."""

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
    """Evalúa las reglas de Variables globales y locales sobre el contexto del archivo."""
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
    # 0x20XXh: Funciones y Modularización
    # -------------------------------------------------------------------------

    # 0x2004h: Variables globales mutables
    if ctx.esta_activa("0x2004h") and not es_header:
        re_global = re.compile(rf"^({TIPOS_BASICOS})\s+(\*?[a-zA-Z_]\w*)\s*(?:=\s*[^;]+)?\s*;", re.MULTILINE)
        for m in re_global.finditer(codigo_sin_comentarios):
            line_no = codigo_sin_comentarios[:m.start()].count("\n") + 1
            line_txt = lineas[line_no - 1].strip()
            if not line_txt.startswith("const") and not line_txt.startswith("typedef") and not line_txt.startswith("static const"):
                rcode, tit = ctx.regla_info("0x2004h")
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

    # -------------------------------------------------------------------------
    # 0x2007h: Mantené el alcance de las variables al mínimo posible
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x2006h"):
        re_for_outer = re.compile(r"^\s*(?:int|size_t)\s+([a-zA-Z_]\w*)\s*;", re.MULTILINE)
        for m_var in re_for_outer.finditer(codigo_sin_comentarios):
            vname = m_var.group(1)
            if re.search(rf"\bfor\s*\(\s*{vname}\s*=\s*0", codigo_sin_comentarios[m_var.end():]):
                linea_num = contenido_original[:m_var.start()].count("\n") + 1
                rcode, tit = ctx.regla_info("0x2006h")
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
    # 0x3010h: Variables de tamaño o índice deben ser de tipo size_t
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x3010h"):
        re_int_size = re.compile(r"\bint\s+((?:tamano|tamanio|longitud|cantidad|len|tam|sz)\w*)\s*(?:=|;)", re.IGNORECASE)
        re_int_sizeof_assign = re.compile(r"\bint\s+([a-zA-Z_]\w*)\s*=\s*(?:sizeof|strlen)\s*\(")
        for i, l in enumerate(lineas_sin_comentarios):
            m_sz = re_int_size.search(l)
            if m_sz:
                vname = m_sz.group(1)
                rcode, tit = ctx.regla_info("0x3010h")
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
                    rcode, tit = ctx.regla_info("0x3010h")
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
    # 0x100Ch: Exigencia de break explícito o comentario de fallthrough en bloques switch case
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x100Bh"):
        re_case_block = re.compile(r"\bcase\s+[^:]+:\s*\n((?:[^\n]+\n)*?)(?=\s*(?:case\s+[^:]+|default)\s*:)", re.MULTILINE)
        for m_cb in re_case_block.finditer(codigo_sin_comentarios):
            c_body = m_cb.group(1).strip()
            if c_body:
                if not (re.search(r"\b(?:break|return)\s*;", c_body) or "fallthrough" in c_body.lower()):
                    linea_num = contenido_original[:m_cb.start()].count("\n") + 1
                    rcode, tit = ctx.regla_info("0x100Bh")
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
    # 0x200Ch: Prohibición de retornar la dirección de una variable local de stack
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x200Bh"):
        re_ret_addr = re.compile(r"^\s*return\s+&\s*([a-zA-Z_]\w*)\s*;", re.MULTILINE)
        for i, l in enumerate(lineas_sin_comentarios):
            m_ra = re_ret_addr.match(l)
            if m_ra:
                vnom = m_ra.group(1)
                rcode, tit = ctx.regla_info("0x200Bh")
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
    # 0x100Ch: Detección de comparaciones en estilo Yoda (CONST == var)
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x100Bh"):
        re_yoda = re.compile(r"\b(NULL|0|[1-9]\d*|true|false)\s*(==|!=)\s*([a-zA-Z_]\w*(?:->\w+|\.\w+|\[[^\]]+\])?)")
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("#") or l.strip().startswith("*") or l.strip().startswith("//"):
                continue
            for m in re_yoda.finditer(l):
                val_const = m.group(1)
                op = m.group(2)
                var_ident = m.group(3)
                rcode, tit = ctx.regla_info("0x100Bh")
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
    # 0x2012h: Prohibición de asignaciones múltiples consecutivas sin lectura intermedia (dead store)
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x2011h"):
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
                    rcode, tit = ctx.regla_info("0x2011h")
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
    # 0x0023h: Detector de variables locales no inicializadas con modificador const
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x301Ch"):
        re_const_uninit = re.compile(r"\bconst\s+(?:struct\s+\w+|\w+)\s*(\*+)?\s*([a-zA-Z_]\w*)\s*;")
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("//") or l.strip().startswith("/*") or l.strip().startswith("#"):
                continue
            m_cu = re_const_uninit.search(l)
            if m_cu:
                var_n = m_cu.group(2)
                rcode, tit = ctx.regla_info("0x301Ch")
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

    return violaciones
