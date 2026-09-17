"""Reglas de estilo de cátedra — Convenciones léxicas y nombres (rules_10xx)."""

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
    """Evalúa las reglas de Convenciones léxicas y nombres sobre el contexto del archivo."""
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
    # 0x000Ch: Nombres de archivo en snake_case en minúsculas (sin espacios)
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x0104h"):
        nombre_archivo = ruta.name
        es_valido_snake = bool(re.match(r"^[a-z0-9_]+(?:\.[a-z0-9_]+)+$", nombre_archivo))
        if not es_valido_snake:
            sugerido = re.sub(r"[-\s]+", "_", nombre_archivo.lower())
            sugerido = re.sub(r"[^a-z0-9_\.]", "", sugerido)
            rcode, tit = ctx.regla_info("0x0104h")
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

    # 0x0008h: Constantes en MAYUSCULAS_SNAKE_CASE
    if ctx.esta_activa("0x0103h"):
        re_define_const = re.compile(r"^\s*#\s*define\s+([a-zA-Z_]\w*)\s+[\d\.\"\']", re.MULTILINE)
        for m in re_define_const.finditer(codigo_sin_comentarios):
            name = m.group(1)
            if name != name.upper():
                line_no = codigo_sin_comentarios[:m.start()].count("\n") + 1
                rcode, tit = ctx.regla_info("0x0103h")
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
    # 0x000Eh: Nombres de funciones en snake_case estricto
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x0105h"):
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
                rcode, tit = ctx.regla_info("0x0105h")
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
    # 0x0012h: Variables globales deben ser static o usar prefijo g_
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x0106h"):
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
                    rcode, tit = ctx.regla_info("0x0106h")
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
    # 0x0013h: Macros #define deben nombrarse en MAYUSCULAS_SNAKE_CASE
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x0107h"):
        re_macro_min = re.compile(r"^[ \t]*#define[ \t]+([a-z]\w*)", re.MULTILINE)
        for i, l in enumerate(lineas_sin_comentarios):
            m_mac = re_macro_min.match(l)
            if m_mac:
                macro_nom = m_mac.group(1)
                rcode, tit = ctx.regla_info("0x0107h")
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
    # 0x0014h: Auditor de tipografía y prohibición de caracteres no ASCII en código
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x0108h"):
        for i, l in enumerate(lineas_sin_cadenas):
            if not l.strip() or l.strip().startswith(("//", "/*", "*")):
                continue
            re_typo = re.search(r"[“”‘’«»–—− ​﻿]", l)
            if re_typo:
                char_bad = re_typo.group(0)
                codepoint = f"U+{ord(char_bad):04X}"
                rcode, tit = ctx.regla_info("0x0108h")
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
                rcode, tit = ctx.regla_info("0x0108h")
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
    # 0x0016h: Prohibición de identificadores que colisionen con palabras clave o tipos estándar
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x0109h"):
        re_res_id = re.compile(rf"\b(?:{TIPOS_BASICOS})\s+(restrict|inline|bool|true|false|nullptr|alignas)\b")
        for i, l in enumerate(lineas_sin_comentarios):
            m_ri = re_res_id.search(l)
            if m_ri:
                nom = m_ri.group(1)
                rcode, tit = ctx.regla_info("0x0109h")
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
    # 0x0018h: Prohibición de identificadores con prefijos reservados (__ o _[A-Z])
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x010Ah"):
        re_res_pref = re.compile(rf"\b(?:{TIPOS_BASICOS})\s+(__\w+|_([A-Z]\w*))\b")
        for i, l in enumerate(lineas_sin_comentarios):
            m_rp = re_res_pref.search(l)
            if m_rp:
                nom = m_rp.group(1)
                rcode, tit = ctx.regla_info("0x010Ah")
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
    # 0x0038h: Prohibición de constantes numéricas mágicas en índices de arreglos
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x010Fh"):
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
                rcode, tit = ctx.regla_info("0x010Fh")
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
    # 0x0020h: Proporcionalidad en longitud de identificadores según su alcance
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x010Bh"):
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
                        rcode, tit = ctx.regla_info("0x010Bh")
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
                            rcode, tit = ctx.regla_info("0x010Bh")
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
    # 0x0026h: Auditor de identificadores reservados (__ o _[A-Z])
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x010Ch"):
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
                rcode, tit = ctx.regla_info("0x010Ch")
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
    # 0x002Ch: Auditor de consistencia en nombres de constantes simbólicas (#define)
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x010Dh"):
        re_macro_const = re.compile(r"^[ \t]*#define[ \t]+([a-zA-Z_]\w*)(?!\s*\()[ \t]+([0-9\"'a-zA-Z_(].*)")
        for i, l in enumerate(lineas_sin_cadenas):
            m_mc = re_macro_const.match(l)
            if m_mc:
                nom_m = m_mc.group(1)
                if any(c.islower() for c in nom_m) and not nom_m.startswith("__"):
                    rcode, tit = ctx.regla_info("0x010Dh")
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

    return violaciones
