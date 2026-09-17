"""Reglas de estilo de cátedra — Comentarios y estructura documental (rules_00xx)."""

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
    """Evalúa las reglas de Comentarios y estructura documental sobre el contexto del archivo."""
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
    # -------------------------------------------------------------------------
    # 0x0015h: Prohibición del operador coma para encadenar sentencias independientes
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x0008h"):
        re_comma_stmt = re.compile(r"^[ \t]*[a-zA-Z_]\w*\s*=[^,;]+,\s*[a-zA-Z_]\w*\s*=[^;]+;", re.MULTILINE)
        for i, l in enumerate(lineas_sin_comentarios):
            if l.strip().startswith("for"):
                continue
            m_cs = re_comma_stmt.match(l)
            if m_cs:
                rcode, tit = ctx.regla_info("0x0008h")
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
    # 0x0017h: Prohibición de notación húngara o prefijos redundantes de tipo en identificadores
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x0009h"):
        re_hungarian = re.compile(rf"\b(?:{TIPOS_BASICOS})\s+((?:int|float|str|arr|char|p_str)_\w+)")
        for i, l in enumerate(lineas_sin_comentarios):
            m_hu = re_hungarian.search(l)
            if m_hu:
                nom = m_hu.group(1)
                rcode, tit = ctx.regla_info("0x0009h")
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
    # 0x0019h: Prohibición de espacios en blanco antes de separadores de sintaxis (; y ,)
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x000Ah"):
        re_space_sep = re.compile(r"[ \t]+([;,])")
        for i, l in enumerate(lineas_sin_comentarios):
            if l.strip().startswith("for") or l.strip().startswith("/*") or l.strip().startswith("*"):
                continue
            for m_ss in re_space_sep.finditer(l):
                sep = m_ss.group(1)
                rcode, tit = ctx.regla_info("0x000Ah")
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
    # 0x001Ah: Prohibición de espacios en blanco alrededor de operadores de acceso a miembros (-> y .)
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x000Bh"):
        re_member = re.compile(r"\b([a-zA-Z0-9_]+)[ \t]+->[ \t]*([a-zA-Z0-9_]+)|\b([a-zA-Z0-9_]+)[ \t]*->[ \t]+([a-zA-Z0-9_]+)|\b([a-zA-Z_]\w*)[ \t]+\.[ \t]*([a-zA-Z_]\w*)|\b([a-zA-Z_]\w*)[ \t]*\.[ \t]+([a-zA-Z_]\w*)")
        for i, l in enumerate(lineas_sin_cadenas):
            m_mem = re_member.search(l)
            if m_mem:
                rcode, tit = ctx.regla_info("0x000Bh")
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
    if ctx.esta_activa("0x000Ch"):
        re_unary = re.compile(r"\b([a-zA-Z_]\w*)[ \t]+(\+\+|\-\-)|(\+\+|\-\-)[ \t]+([a-zA-Z_]\w*)|(!)(?!=)[ \t]+([a-zA-Z_]\w*)")
        for i, l in enumerate(lineas_sin_cadenas):
            m_un = re_unary.search(l)
            if m_un:
                rcode, tit = ctx.regla_info("0x000Ch")
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
    if ctx.esta_activa("0x000Dh"):
        re_comma = re.compile(r',(?=[^\s\n\r/>])')
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("#"):
                continue
            for m_cm in re_comma.finditer(l):
                rcode, tit = ctx.regla_info("0x000Dh")
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
    if ctx.esta_activa("0x000Eh"):
        re_paren_sp = re.compile(r"\([ \t]+(?!\s|\))|(?<!\s|\()[ \t]+\)")
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("#") or l.strip().startswith("*"):
                continue
            m_psp = re_paren_sp.search(l)
            if m_psp:
                rcode, tit = ctx.regla_info("0x000Eh")
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
    if ctx.esta_activa("0x000Fh"):
        re_multi_sp = re.compile(r"(?<=\S)[ \t]{2,}(?=\S)")
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("#") or l.strip().startswith("*"):
                continue
            m_msp = re_multi_sp.search(l)
            if m_msp:
                rcode, tit = ctx.regla_info("0x000Fh")
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
    # 0x0015h: Alineación vertical consistente en asignaciones consecutivas
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x0008h"):
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
                    rcode, tit = ctx.regla_info("0x0008h")
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
    # 0x0017h: Espaciado consistente en declaraciones de doble puntero (tipo **var)
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x0009h"):
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
                    rcode, tit = ctx.regla_info("0x0009h")
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
    # 0x001Fh: Prohibición de llaves redundantes en inicialización de tipos escalares
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x0010h"):
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
                    rcode, tit = ctx.regla_info("0x0010h")
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
    # 0x0022h: Validador de espaciado estricto en sentencias de control
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x0011h"):
        re_ctrl_no_space = re.compile(r"\b(if|for|while|switch)\(")
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("//") or l.strip().startswith("/*") or l.strip().startswith("#"):
                continue
            for m in re_ctrl_no_space.finditer(l):
                rcode, tit = ctx.regla_info("0x0011h")
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
    # 0x0025h: Formato canónico en firmas de punteros a función
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x0012h"):
        re_bad_fn_ptr = re.compile(r"\btypedef\s+[^;]*?\(\s*\*\s+([a-zA-Z_]\w*)\s*\)|\btypedef\s+[^;]*?\(\s*\*\s*([a-zA-Z_]\w*)\s+\)")
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("//") or l.strip().startswith("/*") or l.strip().startswith("#"):
                continue
            m_fp = re_bad_fn_ptr.search(l)
            if m_fp:
                fn_name = m_fp.group(1) or m_fp.group(2)
                rcode, tit = ctx.regla_info("0x0012h")
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
    # 0x0027h: Validador de presencia de cabecera de documentación obligatoria por archivo
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x0206h"):
        primeras = lineas[:20]
        texto_primeras = "\n".join(primeras)
        tiene_cabecera = ("/*" in texto_primeras and "*/" in texto_primeras) or (sum(1 for l in primeras if l.strip().startswith("//")) >= 2)
        if not tiene_cabecera and len(lineas) >= 10:
            rcode, tit = ctx.regla_info("0x0206h")
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
    if ctx.esta_activa("0x0013h"):
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("//") or l.strip().startswith("/*") or l.strip().startswith("#"):
                continue
            stripped = l.strip()
            if stripped.startswith("case ") or stripped.startswith("default:") or "?" in stripped:
                continue
            m_lab = re.match(r"^[ \t]+([a-zA-Z_]\w*)\s*:\s*$", l)
            if m_lab and m_lab.group(1) not in {"default"}:
                lbl_name = m_lab.group(1)
                rcode, tit = ctx.regla_info("0x0013h")
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
    if ctx.esta_activa("0x0014h"):
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
                    rcode, tit = ctx.regla_info("0x0014h")
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
    if ctx.esta_activa("0x0015h"):
        re_bad_comma = re.compile(r"(?:[a-zA-Z_]\w*)\s*\([^;]*?(?:,[^\s\)\],]|\s+,)[^;]*?\)")
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("//") or l.strip().startswith("/*") or l.strip().startswith("#"):
                continue
            if re_bad_comma.search(l):
                rcode, tit = ctx.regla_info("0x0015h")
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
    # 0x002Dh: Validador de espaciado en operadores unarios (*ptr, &var, !flag, ++i)
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x0016h"):
        re_bad_unary = re.compile(r"(?:^|[\s(,=;])(\*|&|!|\+\+|--)[ \t]+([a-zA-Z_]\w*)")
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("//") or l.strip().startswith("/*") or l.strip().startswith("#"):
                continue
            for m_u in re_bad_unary.finditer(l):
                op = m_u.group(1)
                target = m_u.group(2)
                pre = l[:m_u.start(1)].strip()
                if op in {"*", "&"}:
                    if pre and (pre[-1].isalnum() or pre[-1] in {")", "]"}) and pre not in {"return", "sizeof"}:
                        continue
                    if pre.endswith("*)") or pre.endswith("&)") or pre.endswith(":") or pre.endswith("?"):
                        continue
                rcode, tit = ctx.regla_info("0x0016h")
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

    return violaciones
