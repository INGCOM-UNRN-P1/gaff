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
        if ctx.esta_activa("0x0102h") or ctx.esta_activa("0x2009h"):
            if raw_fn not in IGNORED_VAR_NAMES and any(c.isupper() for c in raw_fn) and any(c.islower() for c in raw_fn):
                rcode_target = "0x2009h" if (ctx.esta_activa("0x2009h") and not ctx.esta_activa("0x0102h")) else "0x0102h"
                rcode, tit = ctx.regla_info(rcode_target)
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
        if ctx.esta_activa("0x0101h"):
            if len(raw_fn) > 31:
                rcode, tit = ctx.regla_info("0x0101h")
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
            if ctx.esta_activa("0x0102h") or ctx.esta_activa("0x2009h"):
                if any(c.isupper() for c in p_name) and any(c.islower() for c in p_name):
                    rcode, tit = ctx.regla_info("0x0102h")
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
            if (ctx.esta_activa("0x010Eh") or ctx.esta_activa("0x0101h")) and _es_identificador_generico_numerado(p_name):
                rule_target = "0x010Eh" if ctx.esta_activa("0x010Eh") else "0x0101h"
                rcode, tit = ctx.regla_info(rule_target)
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
            elif ctx.esta_activa("0x0101h"):
                if len(p_name) == 1:
                    if p_name.lower() not in CANONICAL_INDICES and p_name.lower() not in MATH_PARAM_NAMES:
                        rcode, tit = ctx.regla_info("0x0101h")
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
                    rcode, tit = ctx.regla_info("0x0101h")
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
                    rcode, tit = ctx.regla_info("0x0101h")
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
            if ctx.esta_activa("0x0102h") or ctx.esta_activa("0x2009h"):
                if any(c.isupper() for c in var_name) and any(c.islower() for c in var_name):
                    rcode, tit = ctx.regla_info("0x0102h")
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
            if (ctx.esta_activa("0x010Eh") or ctx.esta_activa("0x0101h")) and _es_identificador_generico_numerado(var_name):
                rule_target = "0x010Eh" if ctx.esta_activa("0x010Eh") else "0x0101h"
                rcode, tit = ctx.regla_info(rule_target)
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
            elif ctx.esta_activa("0x0101h"):
                if len(var_name) == 1:
                    if var_name.lower() not in CANONICAL_INDICES:
                        rcode, tit = ctx.regla_info("0x0101h")
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
                    rcode, tit = ctx.regla_info("0x0101h")
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
                    rcode, tit = ctx.regla_info("0x0101h")
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
            if ctx.esta_activa("0x7001h") and not has_init:
                rcode, tit = ctx.regla_info("0x7001h")
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

        if ctx.esta_activa("0x0102h") or ctx.esta_activa("0x2009h"):
            if any(c.isupper() for c in var_lazo) and any(c.islower() for c in var_lazo):
                rcode, tit = ctx.regla_info("0x0102h")
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
        if (ctx.esta_activa("0x010Eh") or ctx.esta_activa("0x0101h")) and _es_identificador_generico_numerado(var_lazo):
            rule_target = "0x010Eh" if ctx.esta_activa("0x010Eh") else "0x0101h"
            rcode, tit = ctx.regla_info(rule_target)
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
        elif ctx.esta_activa("0x0101h"):
            if len(var_lazo) == 1 and var_lazo.lower() not in CANONICAL_INDICES:
                rcode, tit = ctx.regla_info("0x0101h")
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
                rcode, tit = ctx.regla_info("0x0101h")
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
                rcode, tit = ctx.regla_info("0x0101h")
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

    # -------------------------------------------------------------------------

    return violaciones
