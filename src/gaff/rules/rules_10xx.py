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
