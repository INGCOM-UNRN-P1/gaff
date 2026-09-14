"""Reglas de estilo de cátedra — Memoria y recursos dinámicos (rules_60xx)."""

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
    """Evalúa las reglas de Memoria y recursos dinámicos sobre el contexto del archivo."""
    violaciones: List[ViolacionRegla] = []
    ruta = ctx.ruta
    lineas = ctx.lineas
    codigo_sin_comentarios = ctx.codigo_sin_comentarios
    lineas_sin_comentarios = ctx.lineas_sin_comentarios
    codigo_sin_cadenas = ctx.codigo_sin_cadenas
    lineas_sin_cadenas = ctx.lineas_sin_cadenas
    es_header = ctx.es_header
    contenido_original = ctx.contenido_original


    # 0x3003h: No mezclar asignación y comparación en la misma línea
    if ctx.esta_activa("0x3003h"):
        re_asig_comp = re.compile(r"\b(?:if|while)\s*\(\s*\(\s*[a-zA-Z_]\w*\s*=\s*.+?\)\s*(?:==|!=|<|>|<=|>=)")
        for idx, linea in enumerate(lineas_sin_comentarios, 1):
            m = re_asig_comp.search(linea)
            if m:
                rcode, tit = ctx.regla_info("0x3003h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=idx,
                    columna=m.start() + 1,
                    mensaje="Asignación y comparación combinadas en la misma línea de control.",
                    sugerencia="Separá la asignación en una instrucción previa antes del condicional.",
                    codigo_linea=lineas[idx - 1],
                    es_autofixable=False,
                ))

    # 0x3008h: Comparación de punteros contra 0 en vez de NULL
    if ctx.esta_activa("0x3008h"):
        re_ptr_zero = re.compile(r"\b\w*(?:ptr|nodo|lista|buffer|puntero|archivo|file)\w*\s*(?:==|!=)\s*0\b", re.IGNORECASE)
        for idx, linea in enumerate(lineas_sin_comentarios, 1):
            m = re_ptr_zero.search(linea)
            if m:
                rcode, tit = ctx.regla_info("0x3008h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=idx,
                    columna=m.start() + 1,
                    mensaje="Comparación de puntero contra el literal numérico '0'.",
                    sugerencia="Utilizá explícitamente la constante 'NULL'.",
                    codigo_linea=lineas[idx - 1],
                    es_autofixable=False,
                ))

    # 0x3005h: Punteros triples (***) o más niveles de indirección
    if ctx.esta_activa("0x3005h"):
        re_triple_ptr = re.compile(r"\b\w+\s*\*\*\*\s*\w+")
        for idx, linea in enumerate(lineas_sin_comentarios, 1):
            m = re_triple_ptr.search(linea)
            if m:
                rcode, tit = ctx.regla_info("0x3005h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=idx,
                    columna=m.start() + 1,
                    mensaje="Uso de tres o más niveles de indirección de punteros (***).",
                    sugerencia="Rediseñá la estructura de datos o utilizá encapsulamiento en structs.",
                    codigo_linea=lineas[idx - 1],
                    es_autofixable=False,
                ))

    # 0x300Bh: malloc(literal) sin sizeof
    if ctx.esta_activa("0x300Bh"):
        re_malloc_literal = re.compile(r"\bmalloc\s*\(\s*\d+\s*\)")
        for idx, linea in enumerate(lineas_sin_comentarios, 1):
            m = re_malloc_literal.search(linea)
            if m:
                rcode, tit = ctx.regla_info("0x300Bh")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=idx,
                    columna=m.start() + 1,
                    mensaje=f"Llamada a '{m.group(0)}' con tamaño numérico constante sin sizeof.",
                    sugerencia="Utilizá 'sizeof(*ptr)' o 'sizeof(tipo_t)' para calcular el tamaño dinámicamente.",
                    codigo_linea=lineas[idx - 1],
                    es_autofixable=False,
                ))

    # 0x0035h: TDA con struct no opaco en archivo .h
    if ctx.esta_activa("0x301Dh") and es_header:
        re_struct_body = re.compile(r"^\s*struct\s+\w+\s*\{[^}]+\}\s*;", re.MULTILINE)
        for m in re_struct_body.finditer(codigo_sin_comentarios):
            line_no = codigo_sin_comentarios[:m.start()].count("\n") + 1
            rcode, tit = ctx.regla_info("0x301Dh")
            violaciones.append(ViolacionRegla(
                codigo=rcode,
                titulo=tit,
                archivo=ruta,
                linea=line_no,
                columna=1,
                mensaje="Definición de campos de estructura interna en archivo de cabecera (.h).",
                sugerencia="Ocultá la implementación mediante un TDA con puntero opaco ('typedef struct nombre_t nombre_t;').",
                es_autofixable=False,
            ))

    # -------------------------------------------------------------------------
    # Serie GAFF06x: 0x300Dh, 0x2001h, 0x000Dh
    # -------------------------------------------------------------------------

    # 0x300Dh (GAFF006 / GAFF061): Números mágicos (literales fuera de 0, 1, 2, -1)
    if ctx.esta_activa("0x300Dh"):
        codigo_magicos = codigo_sin_comentarios
        # Los bloques enum son contexto válido para literales numéricos
        for m_enum in list(re.finditer(r"\benum\b[^{;]*\{[^}]*\}", codigo_magicos, re.DOTALL)):
            relleno = "".join("\n" if c == "\n" else " " for c in m_enum.group(0))
            codigo_magicos = codigo_magicos[: m_enum.start()] + relleno + codigo_magicos[m_enum.end():]
        codigo_magicos = enmascarar_literales(codigo_magicos)

        re_num_magico = re.compile(
            r"(?<![\w.])(?:0[xX][0-9a-fA-F]+|\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)(?:[uUlLfF]+)?"
        )
        for idx, linea in enumerate(codigo_magicos.splitlines(), 1):
            linea_strip = linea.strip()
            if linea_strip.startswith("#"):
                continue
            # Ignorar líneas que definen constantes
            if re.match(r"^\s*(?:static\s+)?const\s+", linea):
                continue
            for m in re_num_magico.finditer(linea):
                literal = m.group(0)
                if literal.lower().startswith("0x"):
                    valor = float(int(literal[2:].rstrip("uUlL") or "0", 16))
                else:
                    valor = float(literal.rstrip("uUlLfF"))
                if valor in (0.0, 1.0, 2.0):
                    continue
                col_start = m.start()
                if col_start > 0 and linea[col_start - 1] == "-" and valor == 1.0:
                    continue
                rcode, tit = ctx.regla_info("0x300Dh")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=idx,
                    columna=m.start() + 1,
                    mensaje=f"Número mágico '{literal}' sin contexto: no está definido como constante.",
                    sugerencia=f"Definí una constante descriptiva con #define o enum (ej: '#define MAX_INTENTOS {literal}') y usala en su lugar.",
                    codigo_linea=lineas[idx - 1] if idx - 1 < len(lineas) else "",
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x0036h: Asignar NULL al puntero tras liberar un recurso opaco / destructor TDA
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x301Eh"):
        re_destroy_call = re.compile(r"\b([a-zA-Z0-9_]+(?:_destruir|_destroy|_liberar|_cerrar))\s*\(\s*([a-zA-Z_]\w*)\s*\)\s*;")
        for i, l in enumerate(lineas_sin_comentarios):
            m_dest = re_destroy_call.search(l)
            if m_dest:
                fn_dest = m_dest.group(1)
                pname = m_dest.group(2)
                siguientes = " ".join(lineas_sin_comentarios[i:i + 4])
                tiene_null = bool(re.search(rf"\b{pname}\s*=\s*NULL\s*;", siguientes))
                if not tiene_null:
                    rcode, tit = ctx.regla_info("0x301Eh")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=i + 1,
                        columna=m_dest.start() + 1,
                        mensaje=f"Recurso de TDA liberado mediante '{fn_dest}({pname})' sin anular el puntero '{pname} = NULL;'.",
                        sugerencia=f"Asigná '{pname} = NULL;' tras invocar al destructor para invalidar la referencia en el cliente.",
                        codigo_linea=lineas[i],
                        es_autofixable=False,
                    ))

    # -------------------------------------------------------------------------
    # 0x3001h: Siempre verificar asignación de memoria dinámica contra NULL
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x3001h"):
        re_alloc_call = re.compile(r"\b([a-zA-Z_]\w*)\s*=\s*(?:\([a-zA-Z0-9_* ]+\)\s*)?(?:malloc|calloc|realloc)\s*\(")
        for i, l in enumerate(lineas_sin_comentarios):
            m_alloc = re_alloc_call.search(l)
            if m_alloc:
                pname = m_alloc.group(1)
                siguientes = " ".join(lineas_sin_comentarios[i:i + 7])
                tiene_check = bool(re.search(rf"\bif\s*\(\s*(?:{pname}\s*==\s*NULL|NULL\s*==\s*{pname}|!{pname}|{pname}\s*!=\s*NULL)\b", siguientes))
                if not tiene_check:
                    rcode, tit = ctx.regla_info("0x3001h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=i + 1,
                        columna=m_alloc.start() + 1,
                        mensaje=f"Asignación de memoria dinámica para '{pname}' sin verificación inmediata contra NULL.",
                        sugerencia=f"Agregá 'if ({pname} == NULL) {{ ... }}' inmediatamente después de la asignación.",
                        codigo_linea=lineas[i],
                        es_autofixable=False,
                    ))

    # -------------------------------------------------------------------------
    # 0x3002h: Liberar memoria dinámica y asignar NULL al puntero
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x3002h"):
        re_free_call = re.compile(r"\bfree\s*\(\s*([a-zA-Z_]\w*)\s*\)\s*;")
        for i, l in enumerate(lineas_sin_comentarios):
            m_free = re_free_call.search(l)
            if m_free:
                pname = m_free.group(1)
                siguientes = " ".join(lineas_sin_comentarios[i:i + 4])
                tiene_null = bool(re.search(rf"\b{pname}\s*=\s*NULL\s*;", siguientes))
                if not tiene_null:
                    rcode, tit = ctx.regla_info("0x3002h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=i + 1,
                        columna=m_free.start() + 1,
                        mensaje=f"Memoria liberada con 'free({pname})' sin asignar '{pname} = NULL;' para prevenir punteros colgantes.",
                        sugerencia=f"Colocá '{pname} = NULL;' inmediatamente después de 'free({pname})'.",
                        codigo_linea=lineas[i],
                        es_autofixable=False,
                    ))

    # -------------------------------------------------------------------------
    # 0x3006h: Documentar la propiedad de los recursos al utilizar punteros
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x3006h"):
        re_creator_fn = re.compile(r"^(?:[a-zA-Z_]\w*\*|\w+\s*\*)\s*([a-zA-Z_]\w*(?:_crear|_create|_nuevo|_new))\s*\([^)]*\)\s*\{", re.MULTILINE)
        for m_cr in re_creator_fn.finditer(codigo_sin_comentarios):
            fname = m_cr.group(1)
            linea_fn = contenido_original[:m_cr.start()].count("\n")
            doc_previa = ""
            idx = linea_fn - 1
            while idx >= 0 and lineas[idx].strip():
                doc_previa = lineas[idx] + "\n" + doc_previa
                if "/*" in lineas[idx]:
                    break
                idx -= 1
            if not any(k in doc_previa.lower() for k in ("propiedad", "dueño", "responsable", "liberar", "free", "destruir")):
                rcode, tit = ctx.regla_info("0x3006h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=linea_fn + 1,
                    columna=1,
                    mensaje=f"Función creadora '{fname}' retorna puntero sin documentar la propiedad del recurso ni su liberación.",
                    sugerencia="Añadí en la documentación doxygen quién es el responsable de liberar la memoria.",
                    codigo_linea=lineas[linea_fn] if linea_fn < len(lineas) else "",
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x3007h: Argumentos puntero const si la función no los modifica
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x3007h"):
        re_readonly_fn = re.compile(r"\b(?:void|int|size_t)\s+((?:imprimir|mostrar|calcular|contar|buscar|es|son|verificar)_\w+)\s*\(([^)]+)\)", re.MULTILINE)
        for m_ro in re_readonly_fn.finditer(codigo_sin_comentarios):
            fname = m_ro.group(1)
            params_str = m_ro.group(2)
            for param in params_str.split(","):
                param = param.strip()
                if "*" in param and "const" not in param:
                    linea_num = contenido_original[:m_ro.start()].count("\n") + 1
                    rcode, tit = ctx.regla_info("0x3007h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=linea_num,
                        columna=1,
                        mensaje=f"Parámetro puntero '{param}' en función de solo lectura '{fname}' sin calificador 'const'.",
                        sugerencia=f"Declaralo como 'const {param.strip()}' para garantizar que la función no modifique los datos.",
                        codigo_linea=lineas[linea_num - 1] if linea_num <= len(lineas) else "",
                        es_autofixable=False,
                    ))

    # -------------------------------------------------------------------------
    # 0x3009h: Documentar explícitamente casos donde una función puede retornar NULL
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x3009h"):
        re_fn_ptr = re.compile(r"^(?:[a-zA-Z_]\w*\*|\w+\s*\*)\s*([a-zA-Z_]\w*)\s*\([^)]*\)\s*\{", re.MULTILINE)
        for m_fptr in re_fn_ptr.finditer(codigo_sin_comentarios):
            fn_name = m_fptr.group(1)
            start_idx = m_fptr.end()
            brace_count = 1
            curr_idx = start_idx
            while curr_idx < len(codigo_sin_comentarios) and brace_count > 0:
                ch = codigo_sin_comentarios[curr_idx]
                if ch == "{":
                    brace_count += 1
                elif ch == "}":
                    brace_count -= 1
                curr_idx += 1
            body = codigo_sin_comentarios[start_idx:curr_idx]
            if re.search(r"\breturn\s+NULL\s*;", body):
                linea_fn = contenido_original[:m_fptr.start()].count("\n")
                doc_previa = ""
                idx = linea_fn - 1
                while idx >= 0 and lineas[idx].strip():
                    doc_previa = lineas[idx] + "\n" + doc_previa
                    if "/*" in lineas[idx]:
                        break
                    idx -= 1
                if "NULL" not in doc_previa:
                    rcode, tit = ctx.regla_info("0x3009h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=linea_fn + 1,
                        columna=1,
                        mensaje=f"La función '{fn_name}' retorna puntero y contiene 'return NULL;' pero su documentación no explicita el retorno de NULL.",
                        sugerencia="Añadí en '@return' que retorna NULL en caso de error o elemento inexistente.",
                        codigo_linea=lineas[linea_fn] if linea_fn < len(lineas) else "",
                        es_autofixable=False,
                    ))

    # -------------------------------------------------------------------------
    # 0x300Ah: Utilizá cast explícito al convertir tipos de punteros
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x300Ah"):
        re_impl_cast = re.compile(r"\bint\s*\*\s*([a-zA-Z_]\w*)\s*=\s*(?:mem|buffer|ptr_gen|datos_void)\s*;", re.IGNORECASE)
        for i, l in enumerate(lineas_sin_comentarios):
            m_cast = re_impl_cast.search(l)
            if m_cast:
                rcode, tit = ctx.regla_info("0x300Ah")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_cast.start() + 1,
                    mensaje="Conversión implícita de puntero genérico; se requiere cast explícito '(tipo *)'.",
                    sugerencia="Escribí un cast explícito, por ejemplo: '(int *)mem'.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x300Ch: Límites de arreglos estáticos
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x300Ch"):
        re_arr_decl = re.compile(r"\b(?:int|char|float|double)\s+([a-zA-Z_]\w*)\s*\[\s*(\d+)\s*\]\s*;")
        for m_arr in re_arr_decl.finditer(codigo_sin_comentarios):
            arr_name = m_arr.group(1)
            arr_size = int(m_arr.group(2))
            re_arr_access = re.compile(rf"\b{arr_name}\s*\[\s*(\d+)\s*\]")
            for m_acc in re_arr_access.finditer(codigo_sin_comentarios[m_arr.end():]):
                idx_val = int(m_acc.group(1))
                if idx_val >= arr_size:
                    linea_num = contenido_original[:m_arr.end() + m_acc.start()].count("\n") + 1
                    rcode, tit = ctx.regla_info("0x300Ch")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=linea_num,
                        columna=1,
                        mensaje=f"Acceso fuera de los límites del arreglo '{arr_name}' con índice estático [{idx_val}] (tamaño: {arr_size}).",
                        sugerencia=f"Asegurá que el índice esté dentro del rango válido [0, {arr_size - 1}].",
                        codigo_linea=lineas[linea_num - 1] if linea_num <= len(lineas) else "",
                        es_autofixable=False,
                    ))

    # -------------------------------------------------------------------------
    # 0x300Eh: Documentar comportamiento de funciones al manejar punteros nulos
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x300Eh"):
        re_fn_ptrs = re.compile(r"^(?:[a-zA-Z_]\w*\*?|\w+\s*\*?)\s*([a-zA-Z_]\w*)\s*\(([^)]*\*[a-zA-Z_]\w*[^)]*)\)\s*\{", re.MULTILINE)
        for m_fp in re_fn_ptrs.finditer(codigo_sin_comentarios):
            fn_name = m_fp.group(1)
            linea_fn = contenido_original[:m_fp.start()].count("\n")
            doc_previa = ""
            idx = linea_fn - 1
            while idx >= 0 and lineas[idx].strip():
                doc_previa = lineas[idx] + "\n" + doc_previa
                if "/*" in lineas[idx]:
                    break
                idx -= 1
            if doc_previa and "NULL" not in doc_previa and "@pre" not in doc_previa:
                rcode, tit = ctx.regla_info("0x300Eh")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=linea_fn + 1,
                    columna=1,
                    mensaje=f"La función '{fn_name}' recibe argumentos puntero pero no documenta el comportamiento ante 'NULL' ni precondiciones.",
                    sugerencia="Especificá en la documentación si la función admite punteros NULL o declará '@pre ptr != NULL'.",
                    codigo_linea=lineas[linea_fn] if linea_fn < len(lineas) else "",
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x300Fh: Liberación de memoria en orden inverso
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x300Fh"):
        re_free_matrix = re.compile(r"\bfree\s*\(\s*([a-zA-Z_]\w*)\s*\)\s*;\s*.*?free\s*\(\s*\1\s*\[", re.DOTALL)
        for m_inv in re_free_matrix.finditer(codigo_sin_comentarios):
            m_name = m_inv.group(1)
            linea_num = contenido_original[:m_inv.start()].count("\n") + 1
            rcode, tit = ctx.regla_info("0x300Fh")
            violaciones.append(ViolacionRegla(
                codigo=rcode,
                titulo=tit,
                archivo=ruta,
                linea=linea_num,
                columna=1,
                mensaje=f"Liberación en orden incorrecto: se libera el contenedor principal '{m_name}' antes de sus elementos.",
                sugerencia=f"Liberá primero los elementos internos ('{m_name}[i]') y finalmente el puntero principal.",
                codigo_linea=lineas[linea_num - 1] if linea_num <= len(lineas) else "",
                es_autofixable=False,
            ))

    # -------------------------------------------------------------------------
    # 0x3011h: Si recibe puntero genérico de solo lectura, usar const void*
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x3011h"):
        re_ro_void = re.compile(r"\b(?:void|int|size_t)\s+((?:imprimir|mostrar|comparar|hash|serializar|escribir)_\w*)\s*\(([^)]*)\bvoid\s*\*\s*([a-zA-Z_]\w*)[^)]*\)")
        for m_void in re_ro_void.finditer(codigo_sin_comentarios):
            fn_name = m_void.group(1)
            pname = m_void.group(3)
            full_match = m_void.group(0)
            if "const void" not in full_match:
                linea_num = contenido_original[:m_void.start()].count("\n") + 1
                rcode, tit = ctx.regla_info("0x3011h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=linea_num,
                    columna=1,
                    mensaje=f"Parámetro genérico 'void *{pname}' en función de solo lectura '{fn_name}' sin calificador 'const'.",
                    sugerencia=f"Declaralo como 'const void *{pname}' para garantizar inmutabilidad de la memoria.",
                    codigo_linea=lineas[linea_num - 1] if linea_num <= len(lineas) else "",
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x3012h: Prohibición de aritmética de punteros sobre void*
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x3012h"):
        re_void_decl = re.compile(r"\bvoid\s*\*\s*([a-zA-Z_]\w*)\b")
        void_ptrs = set(re_void_decl.findall(codigo_sin_comentarios))
        for vp in void_ptrs:
            re_void_arith = re.compile(rf"\b{vp}\s*(?:\+\+|\-\-|\+\s*\d+|\-\s*\d+)")
            for i, l in enumerate(lineas_sin_comentarios):
                if "void *" in l:
                    continue
                m_va = re_void_arith.search(l)
                if m_va:
                    rcode, tit = ctx.regla_info("0x3012h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=i + 1,
                        columna=m_va.start() + 1,
                        mensaje=f"Aritmética de punteros sobre 'void *{vp}'. El tipo void carece de tamaño definido en C estándar.",
                        sugerencia=f"Casteá explícitamente a '(char *){vp}' o '(uint8_t *){vp}' antes de sumar offsets.",
                        codigo_linea=lineas[i],
                        es_autofixable=False,
                    ))

    # -------------------------------------------------------------------------
    # 0x3015h: Reallocación segura: no sobreescribir el puntero original directamente
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x3015h"):
        re_unsafe_realloc = re.compile(r"\b([a-zA-Z_]\w*)\s*=\s*(?:\([a-zA-Z0-9_* ]+\)\s*)?realloc\s*\(\s*\1\s*,")
        for i, l in enumerate(lineas_sin_comentarios):
            m_re = re_unsafe_realloc.search(l)
            if m_re:
                pname = m_re.group(1)
                rcode, tit = ctx.regla_info("0x3015h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_re.start() + 1,
                    mensaje=f"Reasignación insegura con realloc: '{pname} = realloc({pname}, ...)'. Provoca fuga si realloc falla y retorna NULL.",
                    sugerencia=f"Asigná a una variable temporal: 'void *tmp = realloc({pname}, ...); if (tmp) {pname} = tmp;'.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x100Dh: Prohibición de modificar la variable de control dentro del cuerpo del for
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x301Bh"):
        re_for_head = re.compile(r"\bfor\s*\(\s*(?:int|size_t)?\s*([a-zA-Z_]\w*)\s*=[^;]*;[^;]*;\s*[^)]*\)\s*\{", re.MULTILINE)
        for m_fh in re_for_head.finditer(codigo_sin_comentarios):
            idx_var = m_fh.group(1)
            start_idx = m_fh.end()
            brace_count = 1
            curr_idx = start_idx
            while curr_idx < len(codigo_sin_comentarios) and brace_count > 0:
                ch = codigo_sin_comentarios[curr_idx]
                if ch == "{":
                    brace_count += 1
                elif ch == "}":
                    brace_count -= 1
                curr_idx += 1
            body_for = codigo_sin_comentarios[start_idx:curr_idx]
            if re.search(rf"\b{idx_var}\s*(?:\+\+|\-\-|\+=|\-=|=)\s*[^=]", body_for):
                linea_num = contenido_original[:m_fh.start()].count("\n") + 1
                rcode, tit = ctx.regla_info("0x301Bh")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=linea_num,
                    columna=1,
                    mensaje=f"Modificación de la variable de iteración '{idx_var}' dentro del cuerpo del lazo 'for'.",
                    sugerencia="Modificá el contador únicamente en la cabecera del lazo o reemplazá el 'for' por un 'while'.",
                    codigo_linea=lineas[linea_num - 1] if linea_num <= len(lineas) else "",
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x3013h: Asignación de memoria con sizeof sobre puntero en lugar del tipo apuntado
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x3013h"):
        re_sizeof_ptr = re.compile(r"\b([a-zA-Z_]\w*)\s*=\s*(?:\([a-zA-Z0-9_* ]+\)\s*)?(?:malloc|calloc)\s*\([^)]*sizeof\s*\(\s*\1\s*\)")
        for i, l in enumerate(lineas_sin_comentarios):
            m_sp = re_sizeof_ptr.search(l)
            if m_sp:
                pnom = m_sp.group(1)
                rcode, tit = ctx.regla_info("0x3013h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_sp.start() + 1,
                    mensaje=f"Uso erróneo de 'sizeof({pnom})' sobre el propio puntero en asignación de memoria.",
                    sugerencia=f"Utilizá 'sizeof(*{pnom})' para alocar según el tamaño del tipo apuntado y no del puntero.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x3014h: Prohibición de doble liberación de memoria (double free)
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x3014h"):
        re_double_free = re.compile(r"\bfree\s*\(\s*([a-zA-Z_]\w*)\s*\)\s*;(?:\s*\n)+\s*free\s*\(\s*\1\s*\)\s*;")
        for m_df in re_double_free.finditer(codigo_sin_comentarios):
            pnom = m_df.group(1)
            linea_num = contenido_original[:m_df.start()].count("\n") + 1
            rcode, tit = ctx.regla_info("0x3014h")
            violaciones.append(ViolacionRegla(
                codigo=rcode,
                titulo=tit,
                archivo=ruta,
                linea=linea_num,
                columna=1,
                mensaje=f"Doble liberación de memoria consecutiva sobre '{pnom}'.",
                sugerencia=f"Eliminá la segunda llamada y asigná '{pnom} = NULL;' tras el primer free.",
                codigo_linea=lineas[linea_num - 1] if linea_num <= len(lineas) else "",
                es_autofixable=False,
            ))

    # -------------------------------------------------------------------------
    # 0x3016h: Prohibición de desreferencia directa de memoria dinámica sin check a NULL previo
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x3016h"):
        re_alloc_deref = re.compile(r"\b([a-zA-Z_]\w*)\s*=\s*(?:\([a-zA-Z0-9_* ]+\)\s*)?(?:malloc|calloc)\s*\([^;]*\)\s*;\s*\n\s*(?:\*\1\b|\1->)")
        for m_ad in re_alloc_deref.finditer(codigo_sin_comentarios):
            pname = m_ad.group(1)
            linea_num = contenido_original[:m_ad.start()].count("\n") + 1
            rcode, tit = ctx.regla_info("0x3016h")
            violaciones.append(ViolacionRegla(
                codigo=rcode,
                titulo=tit,
                archivo=ruta,
                linea=linea_num,
                columna=1,
                mensaje=f"Desreferencia inmediata de '{pname}' tras alocación sin verificación contra NULL.",
                sugerencia=f"Verificá 'if ({pname} == NULL)' antes de desreferenciar el bloque alocado.",
                codigo_linea=lineas[linea_num - 1] if linea_num <= len(lineas) else "",
                es_autofixable=False,
            ))

    # -------------------------------------------------------------------------
    # 0x3017h: Prohibición de utilizar free() como valor o dentro de expresiones compuestas
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x3017h"):
        re_free_val = re.compile(r"(?:\b[a-zA-Z_]\w*\s*=\s*free\s*\(|\(\s*free\s*\([^)]+\)\s*,)")
        for i, l in enumerate(lineas_sin_comentarios):
            m_fv = re_free_val.search(l)
            if m_fv:
                rcode, tit = ctx.regla_info("0x3017h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_fv.start() + 1,
                    mensaje="Uso de 'free()' en una expresión con valor; free() retorna void.",
                    sugerencia="Invocá 'free()' como una sentencia independiente: 'free(p);'.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x3018h: Prohibición de invocar free() sobre punteros declarados con calificador const
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x3018h"):
        re_const_ptr = re.compile(r"\bconst\s+(?:[a-zA-Z0-9_*]+\s+)?\*?\s*([a-zA-Z_]\w*)\s*[=;]")
        const_ptrs = set()
        for l in lineas_sin_comentarios:
            m_cp = re_const_ptr.search(l)
            if m_cp:
                const_ptrs.add(m_cp.group(1))
        if const_ptrs:
            for i, l in enumerate(lineas_sin_comentarios):
                for cp in const_ptrs:
                    if re.search(rf"\bfree\s*\(\s*(?:\([a-zA-Z0-9_* ]+\)\s*)?{cp}\s*\)", l):
                        rcode, tit = ctx.regla_info("0x3018h")
                        violaciones.append(ViolacionRegla(
                            codigo=rcode,
                            titulo=tit,
                            archivo=ruta,
                            linea=i + 1,
                            columna=1,
                            mensaje=f"Invocación de 'free()' sobre el puntero constante '{cp}'.",
                            sugerencia="Los punteros 'const' representan datos de sólo lectura o estáticos que no deben ser liberados.",
                            codigo_linea=lineas[i],
                            es_autofixable=False,
                        ))

    # -------------------------------------------------------------------------
    # 0x3019h: Prohibición de comparar punteros contra constantes numéricas distintas de NULL o cero
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x3019h"):
        re_ptr_decl = re.compile(rf"\b(?:{TIPOS_BASICOS}|[a-zA-Z_]\w*)\s*\*\s*([a-zA-Z_]\w*)\s*[=;,\)]")
        declared_ptrs = set()
        for l in lineas_sin_comentarios:
            for m_pd in re_ptr_decl.finditer(l):
                declared_ptrs.add(m_pd.group(1))
        for i, l in enumerate(lineas_sin_comentarios):
            for dp in declared_ptrs:
                m_cmp = re.search(rf"\b{dp}\s*(?:==|!=|<|>|<=|>=)\s*([1-9]\d*)\b", l)
                if m_cmp:
                    val = m_cmp.group(1)
                    rcode, tit = ctx.regla_info("0x3019h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=i + 1,
                        columna=m_cmp.start() + 1,
                        mensaje=f"Comparación ilegítima de puntero '{dp}' contra el literal numérico '{val}'.",
                        sugerencia="Compará los punteros únicamente contra 'NULL' u otros punteros del mismo bloque.",
                        codigo_linea=lineas[i],
                        es_autofixable=False,
                    ))

    # -------------------------------------------------------------------------
    # 0x3016h: Orden sospechoso de argumentos en llamadas a memset
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x3016h"):
        re_memset = re.compile(r"\bmemset\s*\(\s*([^,]+?)\s*,\s*([^,]+?)\s*,\s*([^)]+?)\s*\)")
        for i, l in enumerate(lineas_sin_cadenas):
            if "memset" not in l:
                continue
            for m in re_memset.finditer(l):
                arg1 = m.group(1).strip()
                arg2 = m.group(2).strip()
                arg3 = m.group(3).strip()
                es_sospechoso = False
                if "sizeof" in arg2.lower() and arg3 in ("0", "'\\0'", "NULL"):
                    es_sospechoso = True
                elif re.search(r"\b(tam|tamano|size|len|longitud|capacidad|count|bytes)\b", arg2, re.IGNORECASE) and arg3 in ("0", "'\\0'", "NULL"):
                    es_sospechoso = True
                elif re.match(r"^\d+$", arg2) and int(arg2) > 1 and arg3 in ("0", "'\\0'", "NULL"):
                    es_sospechoso = True

                if es_sospechoso:
                    rcode, tit = ctx.regla_info("0x3016h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=i + 1,
                        columna=m.start() + 1,
                        mensaje=f"Orden invertido o sospechoso en 'memset({arg1}, {arg2}, {arg3})': el segundo argumento es el valor de relleno y el tercero es el tamaño en bytes.",
                        sugerencia=f"Invertí los argumentos: 'memset({arg1}, {arg3}, {arg2});'.",
                        codigo_linea=lineas[i],
                        es_autofixable=True,
                    ))

    # -------------------------------------------------------------------------
    # 0x100Dh: Prohibición de casts de tipo innecesarios o redundantes
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x301Bh"):
        re_redundant_cast = re.compile(r"\((int|char|long|float|double|size_t)\)\s*(\(?\s*\b\d+(?:\.\d+)?f?\b|\(?(int|char|long|float|double|size_t)\))")
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("#"):
                continue
            for m in re_redundant_cast.finditer(l):
                rcode, tit = ctx.regla_info("0x301Bh")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m.start() + 1,
                    mensaje=f"Cast de tipo redundante o innecesario detectado: '{m.group(0)}'.",
                    sugerencia="Eliminá el cast innecesario para mantener la legibilidad de la expresión.",
                    codigo_linea=lineas[i],
                    es_autofixable=True,
                ))

    # -------------------------------------------------------------------------
    # 0x3017h: Orden canónico de calificadores: 'const tipo'
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x3017h"):
        re_tipo_const = re.compile(rf"\b({TIPOS_BASICOS})\s+const\b(?!\s*\*|\s*\[)")
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("#"):
                continue
            for m in re_tipo_const.finditer(l):
                tipo = m.group(1)
                rcode, tit = ctx.regla_info("0x3017h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m.start() + 1,
                    mensaje=f"Orden no canónico de calificador const ('{tipo} const').",
                    sugerencia=f"Utilizá el orden canónico de la cátedra: 'const {tipo}'.",
                    codigo_linea=lineas[i],
                    es_autofixable=True,
                ))

    # -------------------------------------------------------------------------
    # 0x3018h: Inicialización idiomática de agregados con {0} en lugar de memset
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x3018h"):
        re_decl_var = re.compile(rf"^[ \t]*(?:struct\s+\w+|\w+_t)\s+([a-zA-Z_]\w*)\s*;")
        for i in range(len(lineas_sin_cadenas) - 1):
            m_dec = re_decl_var.match(lineas_sin_cadenas[i])
            if m_dec:
                vname = m_dec.group(1)
                sig_linea = lineas_sin_cadenas[i+1]
                if f"memset(&{vname}," in sig_linea.replace(" ", "") or f"memset(&{vname} " in sig_linea:
                    rcode, tit = ctx.regla_info("0x3018h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=i + 2,
                        columna=1,
                        mensaje=f"Uso de 'memset' inmediato tras declarar la variable '{vname}'.",
                        sugerencia=f"Inicializá idiomáticamente en la propia declaración: '... {vname} = {{0}};'.",
                        codigo_linea=lineas[i+1],
                        es_autofixable=False,
                    ))

    return violaciones
