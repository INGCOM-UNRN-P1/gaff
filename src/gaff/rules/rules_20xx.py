"""Reglas de estilo de cátedra — Tipos y estructuras (rules_20xx)."""

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
    """Evalúa las reglas de Tipos y estructuras sobre el contexto del archivo."""
    violaciones: List[ViolacionRegla] = []
    ruta = ctx.ruta
    lineas = ctx.lineas
    codigo_sin_comentarios = ctx.codigo_sin_comentarios
    lineas_sin_comentarios = ctx.lineas_sin_comentarios
    codigo_sin_cadenas = ctx.codigo_sin_cadenas
    lineas_sin_cadenas = ctx.lineas_sin_cadenas
    es_header = ctx.es_header
    contenido_original = ctx.contenido_original


    # 0x1001h: Estructuras de control sin llaves
    if ctx.esta_activa("0x1001h"):
        re_if_sin_llaves = re.compile(r"^\s*(?:if\s*\([^)]+\)|for\s*\([^)]+\)|while\s*\([^)]+\)|else)\s*([^{};\s][^;]*;)", re.MULTILINE)
        for m in re_if_sin_llaves.finditer(codigo_sin_comentarios):
            line_no = codigo_sin_comentarios[:m.start()].count("\n") + 1
            line_txt = lineas[line_no - 1]
            rcode, tit = ctx.regla_info("0x1001h")
            violaciones.append(ViolacionRegla(
                codigo=rcode,
                titulo=tit,
                archivo=ruta,
                linea=line_no,
                columna=1,
                mensaje="Estructura de control sin bloque de llaves {}.",
                sugerencia="Encerrá siempre el cuerpo de las sentencias de control dentro de llaves {}.",
                codigo_linea=line_txt,
                es_autofixable=False,
            ))

    # 0x2003h: Documentación completa de funciones y prototipos
    if ctx.esta_activa("0x2003h"):
        def _obtener_prototipos_documentados_header(ruta_h: Path) -> Set[str]:
            if not ruta_h.is_file():
                return set()
            try:
                txt_h = ruta_h.read_text(encoding="utf-8")
            except Exception:
                try:
                    txt_h = ruta_h.read_text(encoding="latin-1")
                except Exception:
                    return set()
            lines_h = txt_h.splitlines()
            code_h_sin_comentarios = eliminar_comentarios(txt_h)
            doc_fns: Set[str] = set()
            re_proto_h = re.compile(
                rf"^[ \t]*(?!(?:typedef|return)\b)(?:(?:static|inline|extern|const)[ \t]+)*(?:struct[ \t]+\w+|enum[ \t]+\w+|union[ \t]+\w+|{TIPOS_BASICOS}|[a-zA-Z_]\w*)[ \t]*(\*+[ \t]*|[ \t]+\*?)([a-zA-Z_]\w*)[ \t]*\(([\s\S]*?)\)[ \t]*;",
                re.MULTILINE
            )
            for m_p in re_proto_h.finditer(code_h_sin_comentarios):
                fn_nom = m_p.group(2)
                l_idx = code_h_sin_comentarios[:m_p.start()].count("\n")
                if _tiene_comentario_documentacion(lines_h, l_idx):
                    doc_fns.add(fn_nom)
            return doc_fns

        prototipos_doc_header: Set[str] = set()
        if not es_header:
            comp_h = ruta.with_suffix(".h")
            prototipos_doc_header.update(_obtener_prototipos_documentados_header(comp_h))
            for inc in re.findall(r'#include\s+"([^"]+\.h)"', contenido_original):
                inc_path = ruta.parent / inc
                prototipos_doc_header.update(_obtener_prototipos_documentados_header(inc_path))

        re_fn_decl_all = re.compile(
            rf"^[ \t]*(?!(?:typedef|return)\b)(?:(?:static|inline|extern|const)[ \t]+)*(?:struct[ \t]+\w+|enum[ \t]+\w+|union[ \t]+\w+|{TIPOS_BASICOS}|[a-zA-Z_]\w*)[ \t]*(\*+[ \t]*|[ \t]+\*?)([a-zA-Z_]\w*)[ \t]*\(([\s\S]*?)\)[ \t]*([;{{])?",
            re.MULTILINE
        )

        prototipos_documentados_mismo_archivo: Set[str] = set()
        prototipos_no_documentados: List[Tuple[str, int, int]] = []
        definiciones_no_documentadas: List[Tuple[str, int, int]] = []

        for m_fn in re_fn_decl_all.finditer(codigo_sin_comentarios):
            fn_name = m_fn.group(2)
            if fn_name in ("if", "for", "while", "switch", "return", "sizeof", "main"):
                continue

            line_fn = codigo_sin_comentarios[:m_fn.start(2)].count("\n") + 1
            col_fn = m_fn.start(2) - codigo_sin_comentarios.rfind("\n", 0, m_fn.start(2))
            line_idx_start = codigo_sin_comentarios[:m_fn.start()].count("\n")

            tiene_doc = _tiene_comentario_documentacion(lineas, line_idx_start)

            char_cierre = m_fn.group(4)
            pos_despues_paren = m_fn.end()

            if char_cierre == ";":
                es_prototipo = True
            elif char_cierre == "{":
                es_prototipo = False
            else:
                resto = codigo_sin_comentarios[pos_despues_paren:pos_despues_paren + 100].lstrip()
                if resto.startswith(";"):
                    es_prototipo = True
                elif resto.startswith("{") or "{" in resto[:60]:
                    es_prototipo = False
                else:
                    continue

            if es_prototipo:
                if tiene_doc:
                    prototipos_documentados_mismo_archivo.add(fn_name)
                else:
                    prototipos_no_documentados.append((fn_name, line_fn, col_fn))
            else:
                if not tiene_doc:
                    definiciones_no_documentadas.append((fn_name, line_fn, col_fn))

        rcode, tit = ctx.regla_info("0x2003h")

        if es_header:
            for fn_name, l_no, c_no in prototipos_no_documentados:
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=l_no,
                    columna=c_no,
                    mensaje=f"El prototipo de la función '{fn_name}' no incluye comentario de documentación.",
                    sugerencia="Documentá la función con @brief, @param y @return en formato Doxygen (/** ... */).",
                    codigo_linea=lineas[l_no - 1] if l_no <= len(lineas) else "",
                    es_autofixable=True,
                ))
        else:
            for fn_name, l_no, c_no in prototipos_no_documentados:
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=l_no,
                    columna=c_no,
                    mensaje=f"El prototipo de la función '{fn_name}' no incluye comentario de documentación.",
                    sugerencia="Documentá la función con @brief, @param y @return en formato Doxygen (/** ... */).",
                    codigo_linea=lineas[l_no - 1] if l_no <= len(lineas) else "",
                    es_autofixable=True,
                ))

            for fn_name, l_no, c_no in definiciones_no_documentadas:
                if fn_name in prototipos_documentados_mismo_archivo or fn_name in prototipos_doc_header:
                    continue
                if any(p[0] == fn_name for p in prototipos_no_documentados):
                    continue

                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=l_no,
                    columna=c_no,
                    mensaje=f"La función '{fn_name}' no incluye comentario de documentación.",
                    sugerencia="Documentá la función con @brief, @param y @return en formato Doxygen (/** ... */).",
                    codigo_linea=lineas[l_no - 1] if l_no <= len(lineas) else "",
                    es_autofixable=True,
                ))

    # -------------------------------------------------------------------------
    # 0x30XXh: Punteros y Gestión de Memoria
    # -------------------------------------------------------------------------

    # 0x3004h: Nomenclatura de typedef con _t o t_
    if ctx.esta_activa("0x3004h"):
        re_typedef = re.compile(r"\btypedef\s+(?:struct|enum|union)\s*(?:\w*\s*\{[^}]*\}|\w+)\s+(\w+)\s*;", re.DOTALL)
        for m in re_typedef.finditer(codigo_sin_comentarios):
            tipo_name = m.group(1)
            if not (tipo_name.startswith("t_") or tipo_name.endswith("_t") or tipo_name.startswith("T_")):
                line_no = codigo_sin_comentarios[:m.start(1)].count("\n") + 1
                rcode, tit = ctx.regla_info("0x3004h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=line_no,
                    columna=1,
                    mensaje=f"El tipo definido '{tipo_name}' no utiliza el prefijo 't_' ni el sufijo '_t'.",
                    sugerencia=f"Renombralo como 't_{tipo_name.lower()}' o '{tipo_name.lower()}_t'.",
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x5005h: Organizar la estructura de los archivos .c de forma estándar
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x5005h") and ruta.suffix.lower() == ".c":
        primera_funcion_linea = None
        for i, l in enumerate(lineas_sin_comentarios):
            if re.match(rf"^(?!typedef|extern|static\s+const)\s*{TIPOS_BASICOS}\s+\w+\s*\([^;]*\)", l) and not l.strip().endswith(";"):
                siguientes = [x.strip() for x in lineas_sin_comentarios[i + 1:i + 4] if x.strip()]
                if "{" in l or (siguientes and siguientes[0].startswith("{")):
                    primera_funcion_linea = i + 1
                    break
        
        # Verificación de inclusión de cabeceras de sistema antes de cabeceras de usuario
        user_header_line = None
        user_header_name = None
        stem_h = f"{ruta.stem}.h"
        for i, l in enumerate(lineas_sin_comentarios):
            strip_l = l.strip()
            if strip_l.startswith("#include"):
                m_user = re.match(r'^[ \t]*#include[ \t]+"([^"]+)"', strip_l)
                if m_user:
                    h_u = m_user.group(1)
                    if h_u != stem_h and user_header_line is None:
                        user_header_line = i + 1
                        user_header_name = h_u
                m_sys = re.match(r'^[ \t]*#include[ \t]+<([^>]+)>', strip_l)
                if m_sys and user_header_line is not None:
                    h_s = m_sys.group(1)
                    rcode, tit = ctx.regla_info("0x5005h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=i + 1,
                        columna=1,
                        mensaje=f"Inclusión de cabecera de sistema '<{h_s}>' posterior a cabecera de usuario '{user_header_name}'.",
                        sugerencia="Incluí las cabeceras estándar de sistema (<...>) antes de las cabeceras locales de usuario (\"...\").",
                        codigo_linea=lineas[i],
                        es_autofixable=False,
                    ))
                    break

        if primera_funcion_linea:
            for i in range(primera_funcion_linea, len(lineas)):
                strip_l = lineas[i].strip()
                if strip_l.startswith("#include") or strip_l.startswith("#define"):
                    rcode, tit = ctx.regla_info("0x5005h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=i + 1,
                        columna=1,
                        mensaje=f"Directiva '{strip_l.split()[0]}' ubicada después de la definición de funciones.",
                        sugerencia="Mantené las inclusiones y macros en la sección de cabecera inicial del archivo antes de las funciones.",
                        codigo_linea=lineas[i],
                        es_autofixable=False,
                    ))
                    break

    # -------------------------------------------------------------------------
    # 0x100Bh: Prohibición de estructuras de control con cuerpo vacío (if (...);) o llaves vacías
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x100Ah"):
        re_empty_body = re.compile(r"^[ \t]*(?:if|while|for)\s*\([^)]*\)\s*;\s*$", re.MULTILINE)
        for i, l in enumerate(lineas_sin_comentarios):
            m_eb = re_empty_body.match(l)
            if m_eb:
                rcode, tit = ctx.regla_info("0x100Ah")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_eb.end() - 1,
                    mensaje="Estructura de control con cuerpo nulo: punto y coma ';' inmediatamente después de la condición.",
                    sugerencia="Eliminá el punto y coma ';' y utilizá un bloque con llaves '{ ... }' para encerrar el cuerpo.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))
        re_empty_block = re.compile(r"^[ \t]*(?:if|while|for)\s*\([^)]*\)\s*\{\s*\}\s*$", re.MULTILINE)
        for i, l in enumerate(lineas_sin_comentarios):
            m_ebl = re_empty_block.match(l)
            if m_ebl:
                rcode, tit = ctx.regla_info("0x100Ah")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=1,
                    mensaje="Estructura de control con bloque de llaves vacío '{}'.",
                    sugerencia="Eliminá la estructura vacía o incorporá las instrucciones correspondientes.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x1013h: Prohibición de saltos no estructurados goto hacia atrás o fuera de liberación de recursos
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x1011h"):
        etiquetas_linea: Dict[str, int] = {}
        re_label = re.compile(r"^[ \t]*([a-zA-Z_]\w*)\s*:(?!\s*case\b|\s*default\b)")
        for i, l in enumerate(lineas_sin_cadenas):
            m_lbl = re_label.match(l)
            if m_lbl:
                etiquetas_linea[m_lbl.group(1)] = i + 1

        re_goto = re.compile(r"\bgoto\s+([a-zA-Z_]\w*)\s*;")
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("//") or l.strip().startswith("/*"):
                continue
            for m_g in re_goto.finditer(l):
                target = m_g.group(1)
                goto_line = i + 1
                lbl_line = etiquetas_linea.get(target)
                es_salto_invalido = False
                motivo = ""
                if lbl_line is not None and lbl_line <= goto_line:
                    es_salto_invalido = True
                    motivo = f"Salto hacia atrás (línea {goto_line} -> {lbl_line}) simulando bucle no estructurado."
                elif not re.search(r"(?:clean|err|exit|salir|salida|fin|free|liberar|end)", target, re.IGNORECASE):
                    es_salto_invalido = True
                    motivo = f"Salto a etiqueta '{target}' que no corresponde al patrón canónico de liberación de recursos."

                if es_salto_invalido:
                    rcode, tit = ctx.regla_info("0x1011h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=goto_line,
                        columna=m_g.start() + 1,
                        mensaje=f"Uso no estructurado de 'goto {target}': {motivo}",
                        sugerencia="Reemplazá el salto por estructuras de control estándar ('while', 'for') o reservalo exclusivamente para liberación limpia de recursos al final de la función.",
                        codigo_linea=lineas[i],
                        es_autofixable=False,
                    ))

    # -------------------------------------------------------------------------
    # 0x1014h: Prohibición de expresiones de asignación dentro de estructuras de control
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x1012h"):
        re_ctrl_assign = re.compile(r"\b(if|while|switch)\s*\([^;]*?\(\s*([a-zA-Z_]\w*)\s*=(?!=)\s*[^;]*?\)")
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("//") or l.strip().startswith("/*") or l.strip().startswith("#"):
                continue
            m_ca = re_ctrl_assign.search(l)
            if m_ca:
                rcode, tit = ctx.regla_info("0x1012h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_ca.start() + 1,
                    mensaje=f"Asignación embebida a '{m_ca.group(2)}' dentro de la condición de control '{m_ca.group(1)}'.",
                    sugerencia="Desacoplá la asignación y la evaluación condicional en sentencias separadas para clarificar la lógica y evitar confusiones.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x301Ah: Validador de uso idiomático de tipos booleanos estándar
    # -------------------------------------------------------------------------
    if ctx.esta_activa("0x301Ah"):
        re_bad_bool = re.compile(r"\btypedef\s+(?:int|char|short)\s+([A-Z_]*BOOL[A-Z_]*)\b|#define\s+(TRUE|FALSE)\s+[01]")
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("//") or l.strip().startswith("/*"):
                continue
            m_bb = re_bad_bool.search(l)
            if m_bb:
                nom_bb = m_bb.group(1) or m_bb.group(2)
                rcode, tit = ctx.regla_info("0x301Ah")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_bb.start() + 1,
                    mensaje=f"Redefinición manual no idiomática de tipos booleanos ('{nom_bb}'). Debe utilizarse '<stdbool.h>' estándar.",
                    sugerencia="Incluí '#include <stdbool.h>' y usá los identificadores estándar 'bool', 'true' y 'false'.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    return violaciones
