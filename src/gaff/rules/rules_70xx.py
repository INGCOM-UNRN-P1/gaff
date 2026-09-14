"""Reglas de estilo de cátedra — Entrada/salida y llamadas a sistema (rules_70xx)."""

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
    """Evalúa las reglas de Entrada/salida y llamadas a sistema sobre el contexto del archivo."""
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
    # 0x4001h: Manejá correctamente la apertura y cierre de archivos (validar fopen)
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x4001h"):
        re_fopen_call = re.compile(r"\b([a-zA-Z_]\w*)\s*=\s*fopen\s*\([^;]+\)\s*;")
        for i, l in enumerate(lineas_sin_comentarios):
            m_f = re_fopen_call.search(l)
            if m_f:
                fname = m_f.group(1)
                siguientes = " ".join(lineas_sin_comentarios[i:i + 7])
                tiene_check = bool(re.search(rf"\bif\s*\(\s*(?:{fname}\s*==\s*NULL|NULL\s*==\s*{fname}|!{fname}|{fname}\s*!=\s*NULL)\b", siguientes))
                if not tiene_check:
                    rcode, tit = ctx.regla_info("0x4001h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=i + 1,
                        columna=m_f.start() + 1,
                        mensaje=f"Apertura de archivo '{fname} = fopen(...)' sin comprobación inmediata de retorno contra NULL.",
                        sugerencia=f"Agregá 'if ({fname} == NULL) {{ perror(\"Error\"); return ...; }}' antes de usar el archivo.",
                        codigo_linea=lineas[i],
                        es_autofixable=False,
                    ))

    # -------------------------------------------------------------------------
    # 0x4002h: Validar retornos de operaciones de lectura y escritura de archivos
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x4002h"):
        re_io_ignored = re.compile(r"^\s*(?:(?:void\s*)?\b(fread|fwrite|fscanf)\s*\([^;]+\)\s*;)")
        for i, l in enumerate(lineas_sin_comentarios):
            m_io = re_io_ignored.match(l)
            if m_io:
                fn_io = m_io.group(1)
                rcode, tit = ctx.regla_info("0x4002h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=1,
                    mensaje=f"Llamada a '{fn_io}' descartando su valor de retorno sin validación.",
                    sugerencia=f"Validá el valor de retorno: 'size_t n = {fn_io}(...); if (n < ...) {{ ... }}'.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x4003h: Utilizá errno, perror y strerror para reportar fallos del SO
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x4003h"):
        re_fopen_err = re.compile(r"\bif\s*\(\s*([a-zA-Z_]\w*)\s*==\s*NULL\s*\)\s*\{([^}]+)\}")
        for m_err in re_fopen_err.finditer(codigo_sin_comentarios):
            bloque = m_err.group(2)
            if "printf" in bloque and "perror" not in bloque and "strerror" not in bloque and "errno" not in bloque:
                linea_num = contenido_original[:m_err.start()].count("\n") + 1
                rcode, tit = ctx.regla_info("0x4003h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=linea_num,
                    columna=1,
                    mensaje="Manejo de error de archivo sin invocar a 'perror()' ni reportar 'errno' / 'strerror()'.",
                    sugerencia="Utilizá 'perror(\"Error al abrir archivo\");' o 'strerror(errno)' para reportar el diagnóstico del sistema.",
                    codigo_linea=lineas[linea_num - 1] if linea_num <= len(lineas) else "",
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x4004h: Asegurar simetría de recursos al abrir y cerrar archivos
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x4004h"):
        re_fn_fopen = re.compile(r"^(?:[a-zA-Z_]\w*\*?|\w+\s*\*?)\s*([a-zA-Z_]\w*)\s*\([^)]*\)\s*\{", re.MULTILINE)
        for m_fn in re_fn_fopen.finditer(codigo_sin_comentarios):
            start_idx = m_fn.end()
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
            if "fopen(" in body and "fclose(" not in body:
                linea_num = contenido_original[:m_fn.start()].count("\n") + 1
                rcode, tit = ctx.regla_info("0x4004h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=linea_num,
                    columna=1,
                    mensaje="La función abre un archivo con 'fopen()' pero no realiza el cierre simétrico con 'fclose()'.",
                    sugerencia="Asegurá cerrar todos los descriptores abiertos mediante 'fclose()' al mismo nivel de abstracción.",
                    codigo_linea=lineas[linea_num - 1] if linea_num <= len(lineas) else "",
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x4005h: Evitar offsets y posiciones fijas codificadas a mano en fseek
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x4005h"):
        re_fseek_magic = re.compile(r"\bfseek\s*\(\s*[^,]+\s*,\s*([1-9]\d*)\s*,\s*SEEK_SET\s*\)")
        for i, l in enumerate(lineas_sin_comentarios):
            m_seek = re_fseek_magic.search(l)
            if m_seek:
                off = m_seek.group(1)
                rcode, tit = ctx.regla_info("0x4005h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_seek.start() + 1,
                    mensaje=f"Offset fijo literal '{off}' en 'fseek()'; validá las dimensiones del archivo antes de saltos absolutos.",
                    sugerencia="Calculá el tamaño con 'fseek(f, 0, SEEK_END)' y 'ftell(f)' para verificar el offset antes de mover el cursor.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x4007h: Prohibición de rutas absolutas hardcodeadas en llamadas de archivo
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x4007h"):
        re_abs_path = re.compile(r'\bfopen\s*\(\s*"(?:/(?:home|etc|var|tmp|usr|opt)|[a-zA-Z]:\\\\)')
        for i, l in enumerate(lineas_sin_comentarios):
            m_ap = re_abs_path.search(l)
            if m_ap:
                rcode, tit = ctx.regla_info("0x4007h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_ap.start() + 1,
                    mensaje="Ruta absoluta hardcodeada en llamada a 'fopen()'. Afecta la portabilidad del programa.",
                    sugerencia="Utilizá rutas relativas o recibí el nombre del archivo como argumento en 'argv' o parámetro de función.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x4006h: Prohibición del antipatrón while (!feof(f))
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x4006h"):
        re_while_feof = re.compile(r"\bwhile\s*\(\s*!feof\s*\(")
        for i, l in enumerate(lineas_sin_comentarios):
            m_wf = re_while_feof.search(l)
            if m_wf:
                rcode, tit = ctx.regla_info("0x4006h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_wf.start() + 1,
                    mensaje="Antipatrón de lectura: 'while (!feof(...))' evalúa EOF antes de intentar leer.",
                    sugerencia="Controlá el lazo evaluando el retorno de la operación de lectura: 'while (fgets(...) != NULL)' o 'while (fread(...) == 1)'.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x4008h: Validación obligatoria del valor de retorno de fclose() en modo escritura
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x4008h"):
        re_write_file = re.compile(r'\b([a-zA-Z_]\w*)\s*=\s*fopen\s*\([^)]*"(?:w|a|wb|w\+|a\+)"[^)]*\)\s*;')
        for m_wf in re_write_file.finditer(codigo_sin_comentarios):
            fvar = m_wf.group(1)
            re_ignored_fclose = re.compile(rf"^\s*fclose\s*\(\s*{fvar}\s*\)\s*;", re.MULTILINE)
            for m_ifc in re_ignored_fclose.finditer(codigo_sin_comentarios):
                linea_num = contenido_original[:m_ifc.start()].count("\n") + 1
                rcode, tit = ctx.regla_info("0x4008h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=linea_num,
                    columna=1,
                    mensaje=f"Retorno de 'fclose({fvar})' ignorado en archivo abierto para escritura.",
                    sugerencia=f"Validá 'if (fclose({fvar}) == EOF)' para detectar posibles fallos al vaciar búferes a disco.",
                    codigo_linea=lineas[linea_num - 1] if linea_num <= len(lineas) else "",
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x4009h: Prohibición de anidar llamadas a fopen() directamente dentro de funciones de E/S
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x4009h"):
        re_nested_fopen = re.compile(r"\b(?:fscanf|fread|fwrite|fgets|fgetc|fputc)\s*\([^)]*\bfopen\s*\(")
        for i, l in enumerate(lineas_sin_comentarios):
            m_nf = re_nested_fopen.search(l)
            if m_nf:
                rcode, tit = ctx.regla_info("0x4009h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_nf.start() + 1,
                    mensaje="Llamada anidada directa a 'fopen()' dentro de función de E/S.",
                    sugerencia="Asigná el descriptor a una variable 'FILE *arch = fopen(...);', validalo contra NULL y cerralo con fclose().",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x400Ah: Prohibición de operar sobre flujos de archivo tras haber invocado fclose() (use-after-close)
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x400Ah"):
        re_fclose_var = re.compile(r"\bfclose\s*\(\s*([a-zA-Z_]\w*)\s*\)\s*;")
        for m_fc in re_fclose_var.finditer(codigo_sin_comentarios):
            fvar = m_fc.group(1)
            after_text = codigo_sin_comentarios[m_fc.end():]
            m_uac = re.search(rf"\b(?:fread|fwrite|fgets|fgetc|fputc|fscanf|fprintf|fseek|ftell)\s*\([^)]*\b{fvar}\b", after_text)
            if m_uac:
                pos = m_fc.end() + m_uac.start()
                linea_num = contenido_original[:pos].count("\n") + 1
                rcode, tit = ctx.regla_info("0x400Ah")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=linea_num,
                    columna=1,
                    mensaje=f"Operación de E/S sobre el descriptor de archivo cerrado '{fvar}' (use-after-close).",
                    sugerencia=f"Anulá el puntero '{fvar} = NULL;' tras fclose() y no intentes acceder al flujo cerrado.",
                    codigo_linea=lineas[linea_num - 1] if linea_num <= len(lineas) else "",
                    es_autofixable=False,
                ))

    return violaciones
