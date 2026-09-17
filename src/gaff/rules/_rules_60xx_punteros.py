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
            for m in re_ptr_zero.finditer(linea):
                prefix = linea[:m.start()].rstrip()
                # Descartar si el puntero está desreferenciado (*ptr), se toma su dirección (&ptr) o acceso a miembro
                if prefix.endswith(("*", "&", "->", ".")):
                    continue
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

    return violaciones
