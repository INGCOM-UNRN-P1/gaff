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
