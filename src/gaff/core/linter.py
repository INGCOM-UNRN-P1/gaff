"""Motor de análisis estático y autofix para GAFF con verificación exhaustiva de reglas de cátedra."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import List, Optional, Set, Tuple

from gaff.core.models import ReporteArchivo, ReporteLinting, RuleCode, ViolacionRegla
from gaff.core.rules import CATALOGO_REGLAS


def _eliminar_comentarios(texto: str) -> str:
    """Reemplaza comentarios de bloque y de línea por espacios para no alterar líneas/columnas."""
    def replacer(match):
        s = match.group(0)
        if s.startswith("/"):
            return "".join("\n" if c == "\n" else " " for c in s)
        return s

    pattern = re.compile(
        r"//.*?$|/\*.*?\*/|'(?:\\.|[^\\'])*'|\"(?:\\.|[^\\\"])*\"",
        re.DOTALL | re.MULTILINE,
    )
    return pattern.sub(replacer, texto)


def _enmascarar_literales(texto: str) -> str:
    """Reemplaza literales de cadena y carácter por espacios preservando líneas/columnas."""
    pattern = re.compile(r"'(?:\\.|[^\\'])*'|\"(?:\\.|[^\\\"])*\"", re.DOTALL)
    return pattern.sub(lambda m: "".join("\n" if c == "\n" else " " for c in m.group(0)), texto)


def _tiene_comentario_documentacion(lineas: List[str], line_idx: int) -> bool:
    """Verifica si la línea (0-indexed) está precedida inmediatamente por un comentario de documentación."""
    idx = line_idx - 1
    blank_lines = 0
    while idx >= 0 and not lineas[idx].strip():
        blank_lines += 1
        idx -= 1
        if blank_lines > 2:
            return False

    if idx < 0:
        return False

    linea_anterior = lineas[idx].strip()

    if linea_anterior.endswith("*/"):
        inicio_idx = idx
        bloque_lineas = [lineas[inicio_idx]]
        while inicio_idx >= 0 and "/*" not in lineas[inicio_idx]:
            inicio_idx -= 1
            if inicio_idx >= 0:
                bloque_lineas.append(lineas[inicio_idx])

        if inicio_idx >= 0:
            texto_bloque = "\n".join(reversed(bloque_lineas))
            if "/**" in texto_bloque or "/*!" in texto_bloque:
                return True
            if any(tag in texto_bloque for tag in ("@brief", r"\brief", "@param", r"\param", "@return", r"\return", "@pre", "@post")):
                return True
            contenido_limpio = re.sub(r"/\*+|\*+/|\*", " ", texto_bloque).strip()
            if len(contenido_limpio) >= 8 and not contenido_limpio.startswith(("#", "//", "int ", "void ")):
                return True

    if linea_anterior.startswith("//"):
        bloque_lineas = []
        curr = idx
        while curr >= 0 and lineas[curr].strip().startswith("//"):
            bloque_lineas.append(lineas[curr].strip())
            curr -= 1
        texto_lineas = " ".join(reversed(bloque_lineas))
        if "///" in texto_lineas or "//!" in texto_lineas:
            return True
        if any(tag in texto_lineas for tag in ("@brief", r"\brief", "@param", r"\param", "@return", r"\return")):
            return True
        contenido_limpio = re.sub(r"^/+\s*", "", texto_lineas).strip()
        if len(contenido_limpio) >= 8 and not contenido_limpio.startswith(("#", "int ", "void ", "return ")):
            return True

    return False


# Tipos básicos de C
TIPOS_BASICOS = r"(?:int|unsigned\s+int|short|unsigned\s+short|long|unsigned\s+long|long\s+long|char|unsigned\s+char|float|double|long\s+double|size_t|ssize_t|bool|_Bool|void|FILE|\w+_t|t_\w+)"


def analizar_archivo(
    ruta: Path,
    reglas_excluidas: Optional[Set[str]] = None,
    reglas_habilitadas: Optional[Set[str]] = None,
) -> List[ViolacionRegla]:
    """Analiza un archivo fuente C y retorna las violaciones de estilo encontradas.

    Por diseño pedagógico institucional, la configuración es por EXCLUSIÓN: todas
    las reglas del catálogo se evalúan obligatoriamente salvo las especificadas en
    `reglas_excluidas`.
    """
    ruta = Path(ruta)
    if not ruta.is_file():
        return []

    violaciones: List[ViolacionRegla] = []

    try:
        contenido_original = ruta.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            contenido_original = ruta.read_text(encoding="latin-1")
        except Exception:
            return []

    lineas = contenido_original.splitlines()
    codigo_sin_comentarios = _eliminar_comentarios(contenido_original)
    lineas_sin_comentarios = codigo_sin_comentarios.splitlines()

    es_header = ruta.suffix.lower() in (".h", ".hpp")

    # 1. Normalizar conjunto de reglas excluidas (modo canónico institucional)
    excluidas_norm: Set[str] = set()
    if reglas_excluidas:
        for r in reglas_excluidas:
            r_low = str(r).strip().lower()
            excluidas_norm.add(r_low)
            if r_low.startswith("0x") and not r_low.endswith("h"):
                excluidas_norm.add(r_low + "h")
            elif r_low.startswith("0x") and r_low.endswith("h"):
                excluidas_norm.add(r_low[:-1])
            if r in CATALOGO_REGLAS:
                c = CATALOGO_REGLAS[r].get("codigo", "").lower()
                excluidas_norm.add(c)
                if c.endswith("h"):
                    excluidas_norm.add(c[:-1])

    # 2. Determinar reglas activas
    if reglas_habilitadas is not None:
        # Retrocompatibilidad con tests heredados que pasen lista de inclusión
        reglas_norm = set()
        for r in reglas_habilitadas:
            r_low = str(r).strip().lower()
            reglas_norm.add(r_low)
            if r_low.startswith("0x") and not r_low.endswith("h"):
                reglas_norm.add(r_low + "h")
            if r in CATALOGO_REGLAS:
                reglas_norm.add(CATALOGO_REGLAS[r].get("codigo", "").lower())
        reglas_norm = reglas_norm - excluidas_norm
    else:
        # Por defecto: TODAS las reglas de cátedra activas EXCEPTO las excluidas
        reglas_norm = {k.lower() for k in CATALOGO_REGLAS.keys()} - excluidas_norm

    def _esta_activa(codigo_hex: str) -> bool:
        cod_low = codigo_hex.lower()
        if cod_low in excluidas_norm:
            return False
        if cod_low.endswith("h") and cod_low[:-1] in excluidas_norm:
            return False
        if not cod_low.endswith("h") and (cod_low + "h") in excluidas_norm:
            return False
        return cod_low in reglas_norm

    def _regla_info(codigo_hex: str) -> Tuple[RuleCode, str]:
        info = CATALOGO_REGLAS.get(codigo_hex, {})
        titulo = info.get("titulo", f"Regla {codigo_hex}")
        return RuleCode(codigo_hex), titulo

    # -------------------------------------------------------------------------
    # 0x000Ch: Nombres de archivo en snake_case en minúsculas (sin espacios)
    # -------------------------------------------------------------------------
    if _esta_activa("0x000Ch"):
        nombre_archivo = ruta.name
        es_valido_snake = bool(re.match(r"^[a-z0-9_]+(?:\.[a-z0-9_]+)+$", nombre_archivo))
        if not es_valido_snake:
            sugerido = re.sub(r"[-\s]+", "_", nombre_archivo.lower())
            sugerido = re.sub(r"[^a-z0-9_\.]", "", sugerido)
            rcode, tit = _regla_info("0x000Ch")
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

    # -------------------------------------------------------------------------
    # 0x50XXh: Compilación y Buenas Prácticas
    # -------------------------------------------------------------------------

    # 0x5003h: Guardas de inclusión en cabeceras (.h)
    if _esta_activa("0x5003h") and es_header:
        tiene_pragma = "#pragma once" in contenido_original
        tiene_ifndef = bool(re.search(r"#ifndef\s+\w+", contenido_original) and re.search(r"#define\s+\w+", contenido_original))
        if not (tiene_pragma or tiene_ifndef):
            rcode, tit = _regla_info("0x5003h")
            stem_h = ruta.stem.upper()
            violaciones.append(ViolacionRegla(
                codigo=rcode,
                titulo=tit,
                archivo=ruta,
                linea=1,
                columna=1,
                mensaje="El archivo de cabecera no cuenta con guardas de inclusión (#ifndef / #define o #pragma once).",
                sugerencia=f"Agregá guardas de preprocesador:\n#ifndef {stem_h}_H\n#define {stem_h}_H\n...\n#endif",
                es_autofixable=True,
            ))

    # 0x5004h: Operaciones de cadenas inseguras (strcpy, strcat, sprintf)
    if _esta_activa("0x5004h"):
        re_str_inseguro = re.compile(r"\b(strcpy|strcat|sprintf)\s*\(")
        for idx, linea in enumerate(lineas_sin_comentarios, 1):
            m = re_str_inseguro.search(linea)
            if m:
                fn = m.group(1)
                rcode, tit = _regla_info("0x5004h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=idx,
                    columna=m.start() + 1,
                    mensaje=f"Uso de función de cadena potencialmente insegura '{fn}'.",
                    sugerencia=f"Reemplazá '{fn}' por variantes seguras con límite de buffer (snprintf, strncpy, strncat).",
                    codigo_linea=lineas[idx - 1],
                    es_autofixable=False,
                ))

    # 0x5006h: gets() prohibida y scanf("%s") inseguro
    if _esta_activa("0x5006h"):
        re_gets = re.compile(r"\bgets\s*\(")
        re_scanf_s = re.compile(r'\bscanf\s*\(\s*"[^"]*%s[^"]*"')
        for idx, linea in enumerate(lineas_sin_comentarios, 1):
            m_gets = re_gets.search(linea)
            if m_gets:
                rcode, tit = _regla_info("0x5006h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=idx,
                    columna=m_gets.start() + 1,
                    mensaje="La función 'gets' está prohibida por carecer de control de límites.",
                    sugerencia="Utilizá 'fgets(buffer, sizeof(buffer), stdin)' para lecturas seguras.",
                    codigo_linea=lineas[idx - 1],
                    es_autofixable=False,
                ))
            m_scanf = re_scanf_s.search(linea)
            if m_scanf:
                rcode, tit = _regla_info("0x5006h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=idx,
                    columna=m_scanf.start() + 1,
                    mensaje="Uso de 'scanf(\"%s\")' sin especificar ancho de buffer.",
                    sugerencia="Especificá ancho de buffer o preferí 'fgets'.",
                    codigo_linea=lineas[idx - 1],
                    es_autofixable=False,
                ))

    # 0x5001h: Arreglos de longitud variable (VLAs)
    if _esta_activa("0x5001h") and not es_header:
        re_vla = re.compile(rf"^\s*{TIPOS_BASICOS}\s+\w+\s*\[\s*([a-zA-Z_]\w*)\s*\]\s*;", re.MULTILINE)
        for m in re_vla.finditer(codigo_sin_comentarios):
            var_name = m.group(1)
            # Si el tamaño es una variable con letras minúsculas (no constante en mayúsculas)
            if var_name != var_name.upper():
                line_no = codigo_sin_comentarios[:m.start()].count("\n") + 1
                rcode, tit = _regla_info("0x5001h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=line_no,
                    columna=1,
                    mensaje=f"Declaración de arreglo con longitud variable (VLA) '{m.group(0).strip()}'.",
                    sugerencia="Definí arreglos estáticos con constantes (#define) o utilizá memoria dinámica (malloc).",
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x10XXh: Estructuras de Control y Lazos
    # -------------------------------------------------------------------------

    # 0x1006h: Prohibición de goto
    if _esta_activa("0x1006h"):
        for idx, linea in enumerate(lineas_sin_comentarios, 1):
            m_goto = re.search(r"\bgoto\s+\w+", linea)
            if m_goto:
                rcode, tit = _regla_info("0x1006h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=idx,
                    columna=m_goto.start() + 1,
                    mensaje="Uso de la sentencia 'goto' detectado.",
                    sugerencia="Reemplazá 'goto' por estructuras de control estructuradas (bucles, retornos directos).",
                    codigo_linea=lineas[idx - 1],
                    es_autofixable=False,
                ))

    # 0x1002h: Prohibición de continue
    if _esta_activa("0x1002h"):
        for idx, linea in enumerate(lineas_sin_comentarios, 1):
            m_cont = re.search(r"\bcontinue\s*;", linea)
            if m_cont:
                rcode, tit = _regla_info("0x1002h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=idx,
                    columna=m_cont.start() + 1,
                    mensaje="Uso de la sentencia 'continue' detectado.",
                    sugerencia="Reemplazá 'continue' por banderas lógicas de control en la condición del lazo.",
                    codigo_linea=lineas[idx - 1],
                    es_autofixable=False,
                ))

    # 0x1007h: Prohibición de operador ternario ?:
    if _esta_activa("0x1007h"):
        for idx, linea in enumerate(lineas_sin_comentarios, 1):
            if not linea.strip().startswith("#"):
                m_tern = re.search(r"(?<=\w|\))\s*\?\s*[^:]+\s*:\s*", linea)
                if m_tern:
                    rcode, tit = _regla_info("0x1007h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=idx,
                        columna=m_tern.start() + 1,
                        mensaje="Uso del operador condicional ternario '?:' detectado.",
                        sugerencia="Reemplazá el operador ternario por sentencias if-else estructuradas.",
                        codigo_linea=lineas[idx - 1],
                        es_autofixable=False,
                    ))

    # 0x1001h: Estructuras de control sin llaves
    if _esta_activa("0x1001h"):
        re_if_sin_llaves = re.compile(r"^\s*(?:if\s*\([^)]+\)|for\s*\([^)]+\)|while\s*\([^)]+\)|else)\s*([^{};\s][^;]*;)", re.MULTILINE)
        for m in re_if_sin_llaves.finditer(codigo_sin_comentarios):
            line_no = codigo_sin_comentarios[:m.start()].count("\n") + 1
            line_txt = lineas[line_no - 1]
            rcode, tit = _regla_info("0x1001h")
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

    # 0x1008h: Switch sin default
    if _esta_activa("0x1008h"):
        re_switch = re.compile(r"\bswitch\s*\([^)]+\)\s*\{", re.MULTILINE)
        for m in re_switch.finditer(codigo_sin_comentarios):
            start_pos = m.end() - 1
            line_no = codigo_sin_comentarios[:m.start()].count("\n") + 1
            brace_count = 0
            end_pos = start_pos
            for i in range(start_pos, len(codigo_sin_comentarios)):
                if codigo_sin_comentarios[i] == '{':
                    brace_count += 1
                elif codigo_sin_comentarios[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_pos = i
                        break
            switch_body = codigo_sin_comentarios[start_pos:end_pos]
            if "default:" not in switch_body and "default :" not in switch_body:
                rcode, tit = _regla_info("0x1008h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=line_no,
                    columna=1,
                    mensaje="Instrucción 'switch' sin bloque 'default:'.",
                    sugerencia="Incluí siempre un caso 'default:' para manejar estados no previstos.",
                    es_autofixable=False,
                ))

    # 0x1003h: for(;;) o for(; cond;)
    if _esta_activa("0x1003h"):
        re_for_empty = re.compile(r"\bfor\s*\(\s*;\s*;\s*\)|\bfor\s*\(\s*;\s*[^;]+;\s*\)")
        for idx, linea in enumerate(lineas_sin_comentarios, 1):
            m = re_for_empty.search(linea)
            if m:
                rcode, tit = _regla_info("0x1003h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=idx,
                    columna=m.start() + 1,
                    mensaje="Uso de 'for' como lazo puramente lógico o indefinido.",
                    sugerencia="Utilizá 'while' para lazos condicionales y reservá 'for' para conteo definido.",
                    codigo_linea=lineas[idx - 1],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x00XXh: Sintaxis Básica y Nomenclatura
    # -------------------------------------------------------------------------

    # 0x0004h: Espaciado en palabras clave (if, for, while, switch)
    if _esta_activa("0x0004h"):
        re_kw = re.compile(r"\b(if|for|while|switch)\(")
        for idx, linea in enumerate(lineas_sin_comentarios, 1):
            m_kw = re_kw.search(linea)
            if m_kw:
                kw = m_kw.group(1)
                rcode, tit = _regla_info("0x0004h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=idx,
                    columna=m_kw.start() + 1,
                    mensaje=f"Falta espacio entre palabra clave '{kw}' y el paréntesis de apertura.",
                    sugerencia=f"Escribí '{kw} (' en lugar de '{kw}('",
                    codigo_linea=lineas[idx - 1],
                    es_autofixable=True,
                ))

    # 0x0006h: Asterisco junto al identificador (int* ptr -> int *ptr)
    if _esta_activa("0x0006h"):
        re_ptr_junto_tipo = re.compile(rf"\b{TIPOS_BASICOS}\*\s+([a-zA-Z_]\w*)")
        for idx, linea in enumerate(lineas_sin_comentarios, 1):
            m = re_ptr_junto_tipo.search(linea)
            if m and not linea.strip().startswith("#"):
                rcode, tit = _regla_info("0x0006h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=idx,
                    columna=m.start() + 1,
                    mensaje="El asterisco de puntero está pegado al tipo de dato.",
                    sugerencia="Colocá el asterisco junto al identificador de la variable (ej: 'int *ptr').",
                    codigo_linea=lineas[idx - 1],
                    es_autofixable=True,
                ))

    # 0x0009h: Longitud de línea (> 80 chars)
    if _esta_activa("0x0009h"):
        for idx, linea in enumerate(lineas, 1):
            if len(linea) > 80:
                rcode, tit = _regla_info("0x0009h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=idx,
                    columna=81,
                    mensaje=f"Línea de {len(linea)} caracteres excede el límite máximo de 80 caracteres.",
                    sugerencia="Dividí la instrucción o llamada en múltiples líneas identadas.",
                    codigo_linea=linea[:80] + "...",
                    es_autofixable=False,
                ))

    # 0x0005h: Espacios finales y mezcla de tabuladores
    if _esta_activa("0x0005h"):
        for idx, linea in enumerate(lineas, 1):
            if linea.endswith(" ") or linea.endswith("\t"):
                rcode, tit = _regla_info("0x0005h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=idx,
                    columna=len(linea),
                    mensaje="Espacios en blanco sobrantes al final de la línea (trailing whitespace).",
                    sugerencia="Eliminá los espacios al final de la línea.",
                    codigo_linea=linea,
                    es_autofixable=True,
                ))
            elif "\t" in linea:
                rcode, tit = _regla_info("0x0005h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=idx,
                    columna=linea.find("\t") + 1,
                    mensaje="Uso de tabuladores duros (\\t) detectado.",
                    sugerencia="Reemplazá tabuladores por 4 espacios.",
                    codigo_linea=linea,
                    es_autofixable=True,
                ))

    # 0x0002h: Múltiples declaraciones de variables por línea
    if _esta_activa("0x0002h"):
        re_mult_decl = re.compile(rf"^\s*{TIPOS_BASICOS}\s+\*?[a-zA-Z_]\w*(?:\s*=\s*[^,;]+)?\s*,\s*\*?[a-zA-Z_]\w*", re.MULTILINE)
        for m in re_mult_decl.finditer(codigo_sin_comentarios):
            line_no = codigo_sin_comentarios[:m.start()].count("\n") + 1
            line_txt = lineas[line_no - 1]
            if not line_txt.strip().startswith("typedef") and "(" not in line_txt:
                rcode, tit = _regla_info("0x0002h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=line_no,
                    columna=1,
                    mensaje="Declaración de múltiples variables en una sola línea.",
                    sugerencia="Declará una única variable por línea para mejorar la legibilidad.",
                    codigo_linea=line_txt,
                    es_autofixable=False,
                ))

    # 0x0008h: Constantes en MAYUSCULAS_SNAKE_CASE
    if _esta_activa("0x0008h"):
        re_define_const = re.compile(r"^\s*#\s*define\s+([a-zA-Z_]\w*)\s+[\d\.\"\']", re.MULTILINE)
        for m in re_define_const.finditer(codigo_sin_comentarios):
            name = m.group(1)
            if name != name.upper():
                line_no = codigo_sin_comentarios[:m.start()].count("\n") + 1
                rcode, tit = _regla_info("0x0008h")
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
    RE_GENERIC_NUMBERED_IDENTIFIER = re.compile(
        r"^(?:"
        r"numero|numeros|num|nums|nro|nros|n|"
        r"var|variable|variables|"
        r"dato|datos|val|valor|valores|"
        r"elem|elemento|elementos|"
        r"aux|auxiliar|tmp|temp|"
        r"arg|param|parametro|parametros|"
        r"item|items|cosa|cosas|obj|objeto|objetos|"
        r"entrada|salida|texto|str|string|"
        r"res|resultado|resultados|"
        r"vec|vector|vectores|arr|array|arreglo|arreglos"
        r")_?[0-9]+$",
        re.IGNORECASE,
    )

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
        if _esta_activa("0x0007h") or _esta_activa("0x200Ah"):
            if raw_fn not in IGNORED_VAR_NAMES and any(c.isupper() for c in raw_fn) and any(c.islower() for c in raw_fn):
                rcode, tit = _regla_info("0x0007h")
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
        if _esta_activa("0x0001h"):
            if len(raw_fn) > 31:
                rcode, tit = _regla_info("0x0001h")
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
            if _esta_activa("0x0007h") or _esta_activa("0x200Ah"):
                if any(c.isupper() for c in p_name) and any(c.islower() for c in p_name):
                    rcode, tit = _regla_info("0x0007h")
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

            # 0x0037h / 0x0001h: Identificadores genéricos con sufijo numérico (numero1, num_1, etc.)
            if (_esta_activa("0x0037h") or _esta_activa("0x0001h")) and RE_GENERIC_NUMBERED_IDENTIFIER.match(p_name):
                rule_target = "0x0037h" if _esta_activa("0x0037h") else "0x0001h"
                rcode, tit = _regla_info(rule_target)
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=line_fn,
                    columna=col_p,
                    mensaje=f"Identificador de parámetro '{p_name}' con sufijo numérico genérico denota una elección pobre de nombre.",
                    sugerencia="Elegí un nombre semántico que describa el rol específico del parámetro (ej: 'dividendo', 'divisor') o utilizá un arreglo/estructura.",
                    codigo_linea=lineas[line_fn - 1] if line_fn <= len(lineas) else "",
                    es_autofixable=False,
                    severidad="ADVERTENCIA",
                ))
            # 0x0001h: Parámetros descriptivos (cortos y largos)
            elif _esta_activa("0x0001h"):
                if len(p_name) == 1:
                    if p_name.lower() not in CANONICAL_INDICES and p_name.lower() not in MATH_PARAM_NAMES:
                        rcode, tit = _regla_info("0x0001h")
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
                    rcode, tit = _regla_info("0x0001h")
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
                    rcode, tit = _regla_info("0x0001h")
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
        rf"^\s*(?:static\s+|const\s+|volatile\s+|register\s+)*(?:(?:struct|union|enum)\s+[a-zA-Z_]\w*|{TIPOS_BASICOS}|[A-Z]\w*)\s+(?!\()([^;{{}}]+);",
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
            if _esta_activa("0x0007h") or _esta_activa("0x200Ah"):
                if any(c.isupper() for c in var_name) and any(c.islower() for c in var_name):
                    rcode, tit = _regla_info("0x0007h")
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

            # 0x0037h / 0x0001h: Variables genéricas con sufijo numérico (numero1, num_1, etc.)
            if (_esta_activa("0x0037h") or _esta_activa("0x0001h")) and RE_GENERIC_NUMBERED_IDENTIFIER.match(var_name):
                rule_target = "0x0037h" if _esta_activa("0x0037h") else "0x0001h"
                rcode, tit = _regla_info(rule_target)
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=line_no,
                    columna=col_v,
                    mensaje=f"Identificador de variable '{var_name}' con sufijo numérico genérico denota una elección pobre de nombre.",
                    sugerencia="Elegí un nombre semántico que describa su rol específico en el algoritmo o utilizá un arreglo/estructura si representan datos homogéneos.",
                    codigo_linea=lineas[line_no - 1] if line_no <= len(lineas) else "",
                    es_autofixable=False,
                    severidad="ADVERTENCIA",
                ))
            # 0x0001h: Variables cortas y largas
            elif _esta_activa("0x0001h"):
                if len(var_name) == 1:
                    if var_name.lower() not in CANONICAL_INDICES:
                        rcode, tit = _regla_info("0x0001h")
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
                    rcode, tit = _regla_info("0x0001h")
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
                    rcode, tit = _regla_info("0x0001h")
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
            if _esta_activa("0x0003h") and not has_init:
                rcode, tit = _regla_info("0x0003h")
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

        if _esta_activa("0x0007h") or _esta_activa("0x200Ah"):
            if any(c.isupper() for c in var_lazo) and any(c.islower() for c in var_lazo):
                rcode, tit = _regla_info("0x0007h")
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

        # 0x0037h / 0x0001h: Variables de lazo genéricas con sufijo numérico
        if (_esta_activa("0x0037h") or _esta_activa("0x0001h")) and RE_GENERIC_NUMBERED_IDENTIFIER.match(var_lazo):
            rule_target = "0x0037h" if _esta_activa("0x0037h") else "0x0001h"
            rcode, tit = _regla_info(rule_target)
            violaciones.append(ViolacionRegla(
                codigo=rcode,
                titulo=tit,
                archivo=ruta,
                linea=line_no,
                columna=col_vl,
                mensaje=f"Identificador de lazo '{var_lazo}' con sufijo numérico genérico denota una elección pobre de nombre.",
                sugerencia="Utilizá índices canónicos (i, j, k, n) o identificadores con significado en el dominio.",
                codigo_linea=lineas[line_no - 1] if line_no <= len(lineas) else "",
                es_autofixable=False,
                severidad="ADVERTENCIA",
            ))
        elif _esta_activa("0x0001h"):
            if len(var_lazo) == 1 and var_lazo.lower() not in CANONICAL_INDICES:
                rcode, tit = _regla_info("0x0001h")
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
                rcode, tit = _regla_info("0x0001h")
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
                rcode, tit = _regla_info("0x0001h")
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

    # 0x000Bh: Llaves en la misma línea (estilo K&R en vez de Allman)
    if _esta_activa("0x000Bh"):
        re_knr = re.compile(r"(?:if|for|while|switch|\))\s*\{$")
        for idx, linea in enumerate(lineas_sin_comentarios, 1):
            if re_knr.search(linea.rstrip()) and not linea.strip().startswith("struct") and not linea.strip().startswith("enum"):
                rcode, tit = _regla_info("0x000Bh")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=idx,
                    columna=linea.rfind("{") + 1,
                    mensaje="Llave de apertura '{' ubicada en la misma línea según estilo K&R.",
                    sugerencia="Ubicá la llave de apertura en una línea independiente según el estilo Allman.",
                    codigo_linea=lineas[idx - 1],
                    es_autofixable=True,
                ))

    # -------------------------------------------------------------------------
    # 0x20XXh: Funciones y Modularización
    # -------------------------------------------------------------------------

    # 0x2004h: Variables globales mutables
    if _esta_activa("0x2004h") and not es_header:
        re_global = re.compile(rf"^({TIPOS_BASICOS})\s+(\*?[a-zA-Z_]\w*)\s*(?:=\s*[^;]+)?\s*;", re.MULTILINE)
        for m in re_global.finditer(codigo_sin_comentarios):
            line_no = codigo_sin_comentarios[:m.start()].count("\n") + 1
            line_txt = lineas[line_no - 1].strip()
            if not line_txt.startswith("const") and not line_txt.startswith("typedef") and not line_txt.startswith("static const"):
                rcode, tit = _regla_info("0x2004h")
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

    # 0x2005h: Longitud máxima de función (> 50 líneas)
    if _esta_activa("0x2005h"):
        re_fn_start = re.compile(r"^\s*(?:[a-zA-Z0-9_*]+\s+)+([a-zA-Z0-9_]+)\s*\([^)]*\)\s*\{?", re.MULTILINE)
        for m in re_fn_start.finditer(codigo_sin_comentarios):
            fn_name = m.group(1)
            start_pos = codigo_sin_comentarios.find("{", m.end() - 1)
            if start_pos == -1 or start_pos - m.start() > 120:
                continue
            line_start = codigo_sin_comentarios[:m.start()].count("\n") + 1

            brace_count = 0
            end_pos = start_pos
            for i in range(start_pos, len(codigo_sin_comentarios)):
                if codigo_sin_comentarios[i] == '{':
                    brace_count += 1
                elif codigo_sin_comentarios[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_pos = i
                        break
            line_end = codigo_sin_comentarios[:end_pos].count("\n") + 1
            total_lines = line_end - line_start + 1
            if total_lines > 50:
                rcode, tit = _regla_info("0x2005h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=line_start,
                    columna=1,
                    mensaje=f"Función '{fn_name}' tiene {total_lines} líneas (máximo permitido: 50).",
                    sugerencia="Modularizá la función dividiéndola en funciones auxiliares.",
                    es_autofixable=False,
                ))

    # 0x2002h: printf/scanf en funciones auxiliares
    if _esta_activa("0x2002h") and not es_header:
        re_fn_any = re.compile(r"^\s*(?:[a-zA-Z0-9_*]+\s+)+([a-zA-Z0-9_]+)\s*\([^)]*\)\s*\{?", re.MULTILINE)
        for m in re_fn_any.finditer(codigo_sin_comentarios):
            fn_name = m.group(1)
            if fn_name in ("main",) or fn_name.startswith(("imprimir_", "mostrar_", "print_", "mostrar", "imprimir", "leer_", "pedir_", "log_", "reportar_")):
                continue
            start_pos = codigo_sin_comentarios.find("{", m.end() - 1)
            if start_pos == -1 or start_pos - m.start() > 120:
                continue
            brace_count = 0
            end_pos = start_pos
            for i in range(start_pos, len(codigo_sin_comentarios)):
                if codigo_sin_comentarios[i] == '{':
                    brace_count += 1
                elif codigo_sin_comentarios[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_pos = i
                        break
            fn_body = codigo_sin_comentarios[start_pos:end_pos]
            m_io = re.search(r"\b(printf|scanf)\s*\(", fn_body)
            if m_io:
                io_pos = start_pos + m_io.start()
                line_no = codigo_sin_comentarios[:io_pos].count("\n") + 1
                rcode, tit = _regla_info("0x2002h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=line_no,
                    columna=1,
                    mensaje=f"Función auxiliar de cálculo '{fn_name}' contiene llamadas directas a '{m_io.group(1)}'.",
                    sugerencia="Separá la lógica computacional del código de entrada/salida por consola.",
                    codigo_linea=lineas[line_no - 1],
                    es_autofixable=False,
                ))

    # 0x2003h: Documentación completa de funciones y prototipos
    if _esta_activa("0x2003h"):
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
            code_h_sin_comentarios = _eliminar_comentarios(txt_h)
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

        rcode, tit = _regla_info("0x2003h")

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
    if _esta_activa("0x3004h"):
        re_typedef = re.compile(r"\btypedef\s+(?:struct|enum|union)\s*(?:\w*\s*\{[^}]*\}|\w+)\s+(\w+)\s*;", re.DOTALL)
        for m in re_typedef.finditer(codigo_sin_comentarios):
            tipo_name = m.group(1)
            if not (tipo_name.startswith("t_") or tipo_name.endswith("_t") or tipo_name.startswith("T_")):
                line_no = codigo_sin_comentarios[:m.start(1)].count("\n") + 1
                rcode, tit = _regla_info("0x3004h")
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

    # 0x3003h: No mezclar asignación y comparación en la misma línea
    if _esta_activa("0x3003h"):
        re_asig_comp = re.compile(r"\b(?:if|while)\s*\(\s*\(\s*[a-zA-Z_]\w*\s*=\s*.+?\)\s*(?:==|!=|<|>|<=|>=)")
        for idx, linea in enumerate(lineas_sin_comentarios, 1):
            m = re_asig_comp.search(linea)
            if m:
                rcode, tit = _regla_info("0x3003h")
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
    if _esta_activa("0x3008h"):
        re_ptr_zero = re.compile(r"\b\w*(?:ptr|nodo|lista|buffer|puntero|archivo|file)\w*\s*(?:==|!=)\s*0\b", re.IGNORECASE)
        for idx, linea in enumerate(lineas_sin_comentarios, 1):
            m = re_ptr_zero.search(linea)
            if m:
                rcode, tit = _regla_info("0x3008h")
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
    if _esta_activa("0x3005h"):
        re_triple_ptr = re.compile(r"\b\w+\s*\*\*\*\s*\w+")
        for idx, linea in enumerate(lineas_sin_comentarios, 1):
            m = re_triple_ptr.search(linea)
            if m:
                rcode, tit = _regla_info("0x3005h")
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
    if _esta_activa("0x300Bh"):
        re_malloc_literal = re.compile(r"\bmalloc\s*\(\s*\d+\s*\)")
        for idx, linea in enumerate(lineas_sin_comentarios, 1):
            m = re_malloc_literal.search(linea)
            if m:
                rcode, tit = _regla_info("0x300Bh")
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
    if _esta_activa("0x0035h") and es_header:
        re_struct_body = re.compile(r"^\s*struct\s+\w+\s*\{[^}]+\}\s*;", re.MULTILINE)
        for m in re_struct_body.finditer(codigo_sin_comentarios):
            line_no = codigo_sin_comentarios[:m.start()].count("\n") + 1
            rcode, tit = _regla_info("0x0035h")
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
    if _esta_activa("0x300Dh"):
        codigo_magicos = codigo_sin_comentarios
        # Los bloques enum son contexto válido para literales numéricos
        for m_enum in list(re.finditer(r"\benum\b[^{;]*\{[^}]*\}", codigo_magicos, re.DOTALL)):
            relleno = "".join("\n" if c == "\n" else " " for c in m_enum.group(0))
            codigo_magicos = codigo_magicos[: m_enum.start()] + relleno + codigo_magicos[m_enum.end():]
        codigo_magicos = _enmascarar_literales(codigo_magicos)

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
                rcode, tit = _regla_info("0x300Dh")
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

    # 0x2001h (GAFF025 / GAFF065): Anidación máxima de 3 niveles dentro de funciones
    if _esta_activa("0x2001h"):
        codigo_nesting = _enmascarar_literales(codigo_sin_comentarios)
        re_no_funcion = re.compile(r"^\s*(?:typedef\s+)?(?:struct|enum|union)\b")
        profundidad = 0
        base_funcion: Optional[int] = None
        ultimo_hito = 0
        for i, ch in enumerate(codigo_nesting):
            if ch == "{":
                profundidad += 1
                if base_funcion is None:
                    segmento = "\n".join(
                        ln for ln in codigo_nesting[ultimo_hito:i].splitlines()
                        if not ln.strip().startswith("#")
                    ).strip()
                    if segmento.endswith(")") and "=" not in segmento and not re_no_funcion.match(segmento):
                        base_funcion = profundidad
                elif profundidad - base_funcion == 4:
                    texto_previo = codigo_nesting[ultimo_hito:i].strip()
                    if not texto_previo.endswith("="):
                        line_no = codigo_nesting[:i].count("\n") + 1
                        rcode, tit = _regla_info("0x2001h")
                        violaciones.append(ViolacionRegla(
                            codigo=rcode,
                            titulo=tit,
                            archivo=ruta,
                            linea=line_no,
                            columna=1,
                            mensaje="Anidación de 4 niveles: supera el máximo de 3 niveles permitidos (código en flecha).",
                            sugerencia="Aplicá cláusulas de guarda (retornos tempranos) o extraé funciones auxiliares para reducir la anidación.",
                            codigo_linea=lineas[line_no - 1],
                            es_autofixable=False,
                        ))
                ultimo_hito = i + 1
            elif ch == "}":
                profundidad -= 1
                if base_funcion is not None and profundidad < base_funcion:
                    base_funcion = None
                ultimo_hito = i + 1
            elif ch == ";":
                ultimo_hito = i + 1

    # 0x000Dh: Código comentado (dead code)
    if _esta_activa("0x000Dh"):
        re_codigo_comentado = re.compile(
            r"^\s*(?:"
            r"(?:if|for|while|switch|return|break|continue|else|do)\b"
            r"|[\w\])]+\s*=[^=]"
            r"|.*;\s*$"
            r"|#\s*(?:include|define|ifdef|ifndef|endif|undef|pragma)\b"
            r")"
        )
        re_token_comentario = re.compile(
            r"//.*?$|/\*.*?\*/|'(?:\\.|[^\\'])*'|\"(?:\\.|[^\\\"])*\"",
            re.DOTALL | re.MULTILINE,
        )
        for m in re_token_comentario.finditer(contenido_original):
            token = m.group(0)
            if not token.startswith("/"):
                continue
            if token.startswith("//"):
                lineas_cuerpo = [token[2:].strip()]
            else:
                lineas_cuerpo = []
                for ln in token[2:-2].splitlines():
                    ln = re.sub(r"^\s*\*+\s?", "", ln).strip()
                    if ln:
                        lineas_cuerpo.append(ln)
            linea_code = next((ln for ln in lineas_cuerpo if re_codigo_comentado.match(ln)), None)
            if linea_code is None:
                continue
            line_no = contenido_original[:m.start()].count("\n") + 1
            columna = m.start() - contenido_original.rfind("\n", 0, m.start())
            rcode, tit = _regla_info("0x000Dh")
            violaciones.append(ViolacionRegla(
                codigo=rcode,
                titulo=tit,
                archivo=ruta,
                linea=line_no,
                columna=columna,
                mensaje=f"Código comentado detectado: '{linea_code[:50]}'",
                sugerencia="Eliminá el código comentado: el historial de cambios pertenece al control de versiones.",
                codigo_linea=lineas[line_no - 1],
                es_autofixable=False,
            ))

    # -------------------------------------------------------------------------
    # 0x000Eh: Nombres de funciones en snake_case estricto
    # -------------------------------------------------------------------------
    if _esta_activa("0x000Eh"):
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
                rcode, tit = _regla_info("0x000Eh")
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
    # 0x000Fh: Evitá comentarios obvios, redundantes o vacíos
    # -------------------------------------------------------------------------
    if _esta_activa("0x000Fh"):
        re_comentarios_obvios = re.compile(r"//\s*(?:incrementa|suma|retorna|asigna|TODO|FIXME|\s*$)", re.IGNORECASE)
        for i, l in enumerate(lineas):
            if "//" in l:
                coment = l.split("//", 1)[1].strip()
                if not coment or coment.lower() in ("todo", "fixme") or re.search(r"^(?:incrementa|suma|guarda|asigna|imprime|retorna)\s+\w+", coment, re.IGNORECASE):
                    rcode, tit = _regla_info("0x000Fh")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=i + 1,
                        columna=l.index("//") + 1,
                        mensaje=f"Comentario redundante, obvio o vacío detectado: '// {coment}'",
                        sugerencia="Explicá la justificación algorítmica ('el porqué') en lugar de describir la sintaxis obvia, o eliminá el comentario.",
                        codigo_linea=l,
                        es_autofixable=True,
                    ))

    # -------------------------------------------------------------------------
    # 0x0010h: Longitud máxima de archivos (máx 500 líneas)
    # -------------------------------------------------------------------------
    if _esta_activa("0x0010h") and len(lineas) > 500:
        rcode, tit = _regla_info("0x0010h")
        violaciones.append(ViolacionRegla(
            codigo=rcode,
            titulo=tit,
            archivo=ruta,
            linea=len(lineas),
            columna=1,
            mensaje=f"El archivo supera el límite recomendado de 500 líneas ({len(lineas)} líneas).",
            sugerencia="Modularizá el archivo dividiendo las funciones en módulos/TDAs complementarios con sus cabeceras .h.",
            codigo_linea=lineas[-1] if lineas else "",
            es_autofixable=False,
        ))

    # -------------------------------------------------------------------------
    # 0x0011h: Inclusión de cabecera propia en primer lugar en .c
    # -------------------------------------------------------------------------
    if _esta_activa("0x0011h") and ruta.suffix.lower() == ".c":
        header_propio = f'"{ruta.stem}.h"'
        headers_encontrados = []
        for i, l in enumerate(lineas):
            strip_l = l.strip()
            if strip_l.startswith("#include") and '"' in strip_l:
                headers_encontrados.append((i + 1, strip_l))
        if headers_encontrados and (ruta.parent / f"{ruta.stem}.h").is_file():
            primero_lin, primero_txt = headers_encontrados[0]
            if header_propio not in primero_txt:
                rcode, tit = _regla_info("0x0011h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=primero_lin,
                    columna=1,
                    mensaje=f"La cabecera propia '#include {header_propio}' debe incluirse antes de cualquier otro header de usuario.",
                    sugerencia=f"Colocá '#include {header_propio}' como la primera línea de inclusión para verificar que el header sea autosuficiente.",
                    codigo_linea=lineas[primero_lin - 1],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x0012h: Variables globales deben ser static o usar prefijo g_
    # -------------------------------------------------------------------------
    if _esta_activa("0x0012h"):
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
                    rcode, tit = _regla_info("0x0012h")
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
    # 0x0000h: La claridad y prolijidad son de máxima importancia (sin exceso de líneas vacías)
    # -------------------------------------------------------------------------
    if _esta_activa("0x0000h"):
        blanks = 0
        for i, l in enumerate(lineas):
            if not l.strip():
                blanks += 1
                if blanks >= 4:
                    rcode, tit = _regla_info("0x0000h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=i + 1,
                        columna=1,
                        mensaje="Exceso de líneas en blanco consecutivas (≥ 4). Mantené la prolijidad del archivo.",
                        sugerencia="Reducí los saltos de línea consecutivos para mantener la compacidad del código.",
                        codigo_linea=lineas[i],
                        es_autofixable=True,
                    ))
                    blanks = 0
            else:
                blanks = 0

    # -------------------------------------------------------------------------
    # 0x000Ah: Comentarios que expliquen el "porqué", no el "qué"
    # -------------------------------------------------------------------------
    if _esta_activa("0x000Ah"):
        re_comentario_obvio = re.compile(r"//\s*(?:incrementa\s+\w+\s+en\s+1|aumenta\s+\w+\s+en\s+1|suma\s+1\s+a\s+\w+|asigna\s+\w+\s+a\s+\w+|retorna\s+0\b)", re.IGNORECASE)
        for i, l in enumerate(lineas):
            m_obv = re_comentario_obvio.search(l)
            if m_obv:
                rcode, tit = _regla_info("0x000Ah")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_obv.start() + 1,
                    mensaje="Comentario redundante que describe lo evidente en lugar del porqué de la decisión.",
                    sugerencia="Escribí comentarios que expliquen la justificación o contexto de diseño, no la sintaxis evidente.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x0036h: Asignar NULL al puntero tras liberar un recurso opaco / destructor TDA
    # -------------------------------------------------------------------------
    if _esta_activa("0x0036h"):
        re_destroy_call = re.compile(r"\b([a-zA-Z0-9_]+(?:_destruir|_destroy|_liberar|_cerrar))\s*\(\s*([a-zA-Z_]\w*)\s*\)\s*;")
        for i, l in enumerate(lineas_sin_comentarios):
            m_dest = re_destroy_call.search(l)
            if m_dest:
                fn_dest = m_dest.group(1)
                pname = m_dest.group(2)
                siguientes = " ".join(lineas_sin_comentarios[i:i + 4])
                tiene_null = bool(re.search(rf"\b{pname}\s*=\s*NULL\s*;", siguientes))
                if not tiene_null:
                    rcode, tit = _regla_info("0x0036h")
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
    # 0x1004h: Condiciones complejas deben simplificarse o comentarse
    # -------------------------------------------------------------------------
    if _esta_activa("0x1004h"):
        re_control_cond = re.compile(r"\b(?:if|while)\s*\((.*?)\)\s*\{?", re.DOTALL)
        for m in re_control_cond.finditer(codigo_sin_comentarios):
            cond_texto = m.group(1)
            total_ops = len(re.findall(r"&&", cond_texto)) + len(re.findall(r"\|\|", cond_texto))
            if total_ops >= 3:
                linea_num = contenido_original[:m.start()].count("\n") + 1
                rcode, tit = _regla_info("0x1004h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=linea_num,
                    columna=1,
                    mensaje=f"Condición lógica compleja con {total_ops} operadores lógicos. Simplificala con variables booleanas intermedias.",
                    sugerencia="Dividí la condición en variables booleanas explicativas (ej: 'bool puede_acceder = ...;').",
                    codigo_linea=lineas[linea_num - 1] if linea_num <= len(lineas) else "",
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x1005h: Evitar condiciones ambiguas por truthiness (strcmp, punteros, chars)
    # -------------------------------------------------------------------------
    if _esta_activa("0x1005h"):
        re_not_strcmp = re.compile(r"\b(?:if|while)\s*\(\s*!\s*str(?:n)?(?:case)?cmp\s*\(")
        re_not_ptr = re.compile(r"\b(?:if|while)\s*\(\s*!\s*([a-zA-Z_]\w*(?:_ptr|ptr|p))\s*\)")
        re_not_char = re.compile(r"\b(?:if|while)\s*\(\s*!\s*([a-zA-Z_]\w*\[[^\]]+\])\s*\)")

        for i, l in enumerate(lineas_sin_comentarios):
            m1 = re_not_strcmp.search(l)
            if m1:
                rcode, tit = _regla_info("0x1005h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m1.start() + 1,
                    mensaje="Condición ambigua: uso de '!strcmp(...)' en lugar de comparación explícita contra 0.",
                    sugerencia="Compará explícitamente: 'if (strcmp(...) == 0)' para clarificar la igualdad.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))
            m2 = re_not_ptr.search(l)
            if m2:
                p_name = m2.group(1)
                rcode, tit = _regla_info("0x1005h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m2.start() + 1,
                    mensaje=f"Condición ambigua por veracidad implícita: '!{p_name}'.",
                    sugerencia=f"Compará el puntero explícitamente contra NULL: 'if ({p_name} == NULL)'.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))
            m3 = re_not_char.search(l)
            if m3:
                c_expr = m3.group(1)
                rcode, tit = _regla_info("0x1005h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m3.start() + 1,
                    mensaje=f"Condición ambigua por veracidad implícita: '!{c_expr}'.",
                    sugerencia=f"Compará el carácter explícitamente contra el nulo: 'if ({c_expr} == \'\\0\')'.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x2006h: Una aserción por cada función de prueba
    # -------------------------------------------------------------------------
    if _esta_activa("0x2006h"):
        re_fn_test = re.compile(r"^(?:void|int)\s+((?:test|prueba)_\w+)\s*\([^)]*\)\s*\{", re.MULTILINE)
        for m_test in re_fn_test.finditer(codigo_sin_comentarios):
            fn_name = m_test.group(1)
            start_idx = m_test.end()
            brace_count = 1
            curr_idx = start_idx
            while curr_idx < len(codigo_sin_comentarios) and brace_count > 0:
                ch = codigo_sin_comentarios[curr_idx]
                if ch == "{":
                    brace_count += 1
                elif ch == "}":
                    brace_count -= 1
                curr_idx += 1
            fn_body = codigo_sin_comentarios[start_idx:curr_idx]
            asserts = len(re.findall(r"\b(?:assert|mu_assert|munit_assert)\s*\(", fn_body))
            if asserts > 1:
                linea_num = contenido_original[:m_test.start()].count("\n") + 1
                rcode, tit = _regla_info("0x2006h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=linea_num,
                    columna=1,
                    mensaje=f"La función de prueba '{fn_name}' contiene {asserts} aserciones (máximo permitido: 1).",
                    sugerencia="Dividí la prueba en casos unitarios separados con una aserción cada uno.",
                    codigo_linea=lineas[linea_num - 1] if linea_num <= len(lineas) else "",
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x2007h: Mantené el alcance de las variables al mínimo posible
    # -------------------------------------------------------------------------
    if _esta_activa("0x2007h"):
        re_for_outer = re.compile(r"^\s*(?:int|size_t)\s+([a-zA-Z_]\w*)\s*;", re.MULTILINE)
        for m_var in re_for_outer.finditer(codigo_sin_comentarios):
            vname = m_var.group(1)
            if re.search(rf"\bfor\s*\(\s*{vname}\s*=\s*0", codigo_sin_comentarios[m_var.end():]):
                linea_num = contenido_original[:m_var.start()].count("\n") + 1
                rcode, tit = _regla_info("0x2007h")
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
    # 0x2008h: Valores de retorno numéricos deben ser constantes o enums
    # -------------------------------------------------------------------------
    if _esta_activa("0x2008h"):
        re_magic_ret = re.compile(r"^\s*return\s+(-?[1-9]\d*)\s*;", re.MULTILINE)
        for i, l in enumerate(lineas_sin_comentarios):
            m_ret = re_magic_ret.match(l)
            if m_ret:
                es_main_o_test = False
                for j in range(i, -1, -1):
                    if "int main(" in lineas_sin_comentarios[j] or "main(" in lineas_sin_comentarios[j]:
                        es_main_o_test = True
                        break
                    if re.search(r"\b(?:test|prueba)_\w+\s*\(", lineas_sin_comentarios[j]):
                        es_main_o_test = True
                        break
                    if lineas_sin_comentarios[j].startswith("}"):
                        break
                if not es_main_o_test:
                    val = m_ret.group(1)
                    rcode, tit = _regla_info("0x2008h")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=i + 1,
                        columna=1,
                        mensaje=f"Retorno de valor numérico mágico '{val}' en lugar de constante o enumeración.",
                        sugerencia="Definí un enum con nombres de estado o constantes como RETORNO_EXITO / ERROR_INVALIDO.",
                        codigo_linea=lineas[i],
                        es_autofixable=False,
                    ))

    # -------------------------------------------------------------------------
    # 0x2009h: Los ejercicios deben ser resueltos mediante funciones (no monolítico en main)
    # -------------------------------------------------------------------------
    if _esta_activa("0x2009h") and ruta.suffix.lower() == ".c":
        re_main_block = re.compile(r"int\s+main\s*\([^)]*\)\s*\{", re.MULTILINE)
        m_main = re_main_block.search(codigo_sin_comentarios)
        if m_main:
            todas_fns = re.findall(rf"^(?!typedef|extern|static\s+const)\s*{TIPOS_BASICOS}\s+(\w+)\s*\([^;]*\)\s*\{{", codigo_sin_comentarios, re.MULTILINE)
            fns_auxiliares = [f for f in todas_fns if f != "main"]
            if not fns_auxiliares and len(lineas) > 35:
                linea_num = contenido_original[:m_main.start()].count("\n") + 1
                rcode, tit = _regla_info("0x2009h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=linea_num,
                    columna=1,
                    mensaje="El ejercicio concentra toda la lógica en 'main()' sin modularizar en funciones.",
                    sugerencia="Descomponé el problema en funciones con responsabilidades únicas.",
                    codigo_linea=lineas[linea_num - 1] if linea_num <= len(lineas) else "",
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x3001h: Siempre verificar asignación de memoria dinámica contra NULL
    # -------------------------------------------------------------------------
    if _esta_activa("0x3001h"):
        re_alloc_call = re.compile(r"\b([a-zA-Z_]\w*)\s*=\s*(?:\([a-zA-Z0-9_* ]+\)\s*)?(?:malloc|calloc|realloc)\s*\(")
        for i, l in enumerate(lineas_sin_comentarios):
            m_alloc = re_alloc_call.search(l)
            if m_alloc:
                pname = m_alloc.group(1)
                siguientes = " ".join(lineas_sin_comentarios[i:i + 7])
                tiene_check = bool(re.search(rf"\bif\s*\(\s*(?:{pname}\s*==\s*NULL|NULL\s*==\s*{pname}|!{pname}|{pname}\s*!=\s*NULL)\b", siguientes))
                if not tiene_check:
                    rcode, tit = _regla_info("0x3001h")
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
    if _esta_activa("0x3002h"):
        re_free_call = re.compile(r"\bfree\s*\(\s*([a-zA-Z_]\w*)\s*\)\s*;")
        for i, l in enumerate(lineas_sin_comentarios):
            m_free = re_free_call.search(l)
            if m_free:
                pname = m_free.group(1)
                siguientes = " ".join(lineas_sin_comentarios[i:i + 4])
                tiene_null = bool(re.search(rf"\b{pname}\s*=\s*NULL\s*;", siguientes))
                if not tiene_null:
                    rcode, tit = _regla_info("0x3002h")
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
    if _esta_activa("0x3006h"):
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
                rcode, tit = _regla_info("0x3006h")
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
    if _esta_activa("0x3007h"):
        re_readonly_fn = re.compile(r"\b(?:void|int|size_t)\s+((?:imprimir|mostrar|calcular|contar|buscar|es|son|verificar)_\w+)\s*\(([^)]+)\)", re.MULTILINE)
        for m_ro in re_readonly_fn.finditer(codigo_sin_comentarios):
            fname = m_ro.group(1)
            params_str = m_ro.group(2)
            for param in params_str.split(","):
                param = param.strip()
                if "*" in param and "const" not in param:
                    linea_num = contenido_original[:m_ro.start()].count("\n") + 1
                    rcode, tit = _regla_info("0x3007h")
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
    if _esta_activa("0x3009h"):
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
                    rcode, tit = _regla_info("0x3009h")
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
    if _esta_activa("0x300Ah"):
        re_impl_cast = re.compile(r"\bint\s*\*\s*([a-zA-Z_]\w*)\s*=\s*(?:mem|buffer|ptr_gen|datos_void)\s*;", re.IGNORECASE)
        for i, l in enumerate(lineas_sin_comentarios):
            m_cast = re_impl_cast.search(l)
            if m_cast:
                rcode, tit = _regla_info("0x300Ah")
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
    if _esta_activa("0x300Ch"):
        re_arr_decl = re.compile(r"\b(?:int|char|float|double)\s+([a-zA-Z_]\w*)\s*\[\s*(\d+)\s*\]\s*;")
        for m_arr in re_arr_decl.finditer(codigo_sin_comentarios):
            arr_name = m_arr.group(1)
            arr_size = int(m_arr.group(2))
            re_arr_access = re.compile(rf"\b{arr_name}\s*\[\s*(\d+)\s*\]")
            for m_acc in re_arr_access.finditer(codigo_sin_comentarios[m_arr.end():]):
                idx_val = int(m_acc.group(1))
                if idx_val >= arr_size:
                    linea_num = contenido_original[:m_arr.end() + m_acc.start()].count("\n") + 1
                    rcode, tit = _regla_info("0x300Ch")
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
    if _esta_activa("0x300Eh"):
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
                rcode, tit = _regla_info("0x300Eh")
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
    if _esta_activa("0x300Fh"):
        re_free_matrix = re.compile(r"\bfree\s*\(\s*([a-zA-Z_]\w*)\s*\)\s*;\s*.*?free\s*\(\s*\1\s*\[", re.DOTALL)
        for m_inv in re_free_matrix.finditer(codigo_sin_comentarios):
            m_name = m_inv.group(1)
            linea_num = contenido_original[:m_inv.start()].count("\n") + 1
            rcode, tit = _regla_info("0x300Fh")
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
    # 0x3010h: Variables de tamaño o índice deben ser de tipo size_t
    # -------------------------------------------------------------------------
    if _esta_activa("0x3010h"):
        re_int_size = re.compile(r"\bint\s+((?:tamano|tamanio|longitud|cantidad|len|tam|sz)\w*)\s*(?:=|;)", re.IGNORECASE)
        re_int_sizeof_assign = re.compile(r"\bint\s+([a-zA-Z_]\w*)\s*=\s*(?:sizeof|strlen)\s*\(")
        for i, l in enumerate(lineas_sin_comentarios):
            m_sz = re_int_size.search(l)
            if m_sz:
                vname = m_sz.group(1)
                rcode, tit = _regla_info("0x3010h")
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
                    rcode, tit = _regla_info("0x3010h")
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
    # 0x3011h: Si recibe puntero genérico de solo lectura, usar const void*
    # -------------------------------------------------------------------------
    if _esta_activa("0x3011h"):
        re_ro_void = re.compile(r"\b(?:void|int|size_t)\s+((?:imprimir|mostrar|comparar|hash|serializar|escribir)_\w*)\s*\(([^)]*)\bvoid\s*\*\s*([a-zA-Z_]\w*)[^)]*\)")
        for m_void in re_ro_void.finditer(codigo_sin_comentarios):
            fn_name = m_void.group(1)
            pname = m_void.group(3)
            full_match = m_void.group(0)
            if "const void" not in full_match:
                linea_num = contenido_original[:m_void.start()].count("\n") + 1
                rcode, tit = _regla_info("0x3011h")
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
    # 0x4001h: Manejá correctamente la apertura y cierre de archivos (validar fopen)
    # -------------------------------------------------------------------------
    if _esta_activa("0x4001h"):
        re_fopen_call = re.compile(r"\b([a-zA-Z_]\w*)\s*=\s*fopen\s*\([^;]+\)\s*;")
        for i, l in enumerate(lineas_sin_comentarios):
            m_f = re_fopen_call.search(l)
            if m_f:
                fname = m_f.group(1)
                siguientes = " ".join(lineas_sin_comentarios[i:i + 7])
                tiene_check = bool(re.search(rf"\bif\s*\(\s*(?:{fname}\s*==\s*NULL|NULL\s*==\s*{fname}|!{fname}|{fname}\s*!=\s*NULL)\b", siguientes))
                if not tiene_check:
                    rcode, tit = _regla_info("0x4001h")
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
    if _esta_activa("0x4002h"):
        re_io_ignored = re.compile(r"^\s*(?:(?:void\s*)?\b(fread|fwrite|fscanf)\s*\([^;]+\)\s*;)")
        for i, l in enumerate(lineas_sin_comentarios):
            m_io = re_io_ignored.match(l)
            if m_io:
                fn_io = m_io.group(1)
                rcode, tit = _regla_info("0x4002h")
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
    if _esta_activa("0x4003h"):
        re_fopen_err = re.compile(r"\bif\s*\(\s*([a-zA-Z_]\w*)\s*==\s*NULL\s*\)\s*\{([^}]+)\}")
        for m_err in re_fopen_err.finditer(codigo_sin_comentarios):
            bloque = m_err.group(2)
            if "printf" in bloque and "perror" not in bloque and "strerror" not in bloque and "errno" not in bloque:
                linea_num = contenido_original[:m_err.start()].count("\n") + 1
                rcode, tit = _regla_info("0x4003h")
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
    if _esta_activa("0x4004h"):
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
                rcode, tit = _regla_info("0x4004h")
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
    if _esta_activa("0x4005h"):
        re_fseek_magic = re.compile(r"\bfseek\s*\(\s*[^,]+\s*,\s*([1-9]\d*)\s*,\s*SEEK_SET\s*\)")
        for i, l in enumerate(lineas_sin_comentarios):
            m_seek = re_fseek_magic.search(l)
            if m_seek:
                off = m_seek.group(1)
                rcode, tit = _regla_info("0x4005h")
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
    # 0x5002h: Desarrollá y compilá siempre con todas las advertencias (prohibido silenciar warnings)
    # -------------------------------------------------------------------------
    if _esta_activa("0x5002h"):
        re_pragma_warn = re.compile(r"#pragma\s+(?:GCC\s+diagnostic\s+ignored|warning\s*\(\s*disable)", re.IGNORECASE)
        for i, l in enumerate(lineas):
            m_pw = re_pragma_warn.search(l)
            if m_pw:
                rcode, tit = _regla_info("0x5002h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_pw.start() + 1,
                    mensaje="Uso de directiva '#pragma' para silenciar advertencias del compilador.",
                    sugerencia="Corregí la causa raíz del warning en el código en lugar de silenciar los diagnósticos del compilador.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))

    # -------------------------------------------------------------------------
    # 0x5005h: Organizar la estructura de los archivos .c de forma estándar
    # -------------------------------------------------------------------------
    if _esta_activa("0x5005h") and ruta.suffix.lower() == ".c":
        primera_funcion_linea = None
        for i, l in enumerate(lineas_sin_comentarios):
            if re.match(rf"^(?!typedef|extern|static\s+const)\s*{TIPOS_BASICOS}\s+\w+\s*\([^;]*\)", l) and not l.strip().endswith(";"):
                siguientes = [x.strip() for x in lineas_sin_comentarios[i + 1:i + 4] if x.strip()]
                if "{" in l or (siguientes and siguientes[0].startswith("{")):
                    primera_funcion_linea = i + 1
                    break
        
        if primera_funcion_linea:
            for i in range(primera_funcion_linea, len(lineas)):
                strip_l = lineas[i].strip()
                if strip_l.startswith("#include") or strip_l.startswith("#define"):
                    rcode, tit = _regla_info("0x5005h")
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

    violaciones.sort(key=lambda v: (v.linea, v.columna))
    return violaciones


def aplicar_autofix_archivo(ruta: Path) -> int:
    """Aplica correcciones automáticas sobre reglas autofixables (GAFF004, GAFF005, GAFF010, GAFF014)."""
    if not ruta.is_file():
        return 0

    try:
        contenido = ruta.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        contenido = ruta.read_text(encoding="latin-1")

    arreglos = 0
    lineas = contenido.splitlines()
    nuevas_lineas = []

    re_kw = re.compile(r"\b(if|for|while|switch)\(")
    re_ptr_fix = re.compile(rf"\b({TIPOS_BASICOS})\*\s+([a-zA-Z_]\w*)")

    for linea in lineas:
        orig = linea
        # GAFF010 / 0x0005h: tabs to spaces y strip trailing
        linea = linea.replace("\t", "    ").rstrip()
        # GAFF007 / 0x0004h: keywords spacing
        linea = re_kw.sub(r"\1 (", linea)
        # GAFF014 / 0x0006h: pointer asterisk spacing
        if not linea.strip().startswith("#"):
            linea = re_ptr_fix.sub(r"\1 *\2", linea)

        if linea != orig:
            arreglos += 1
        nuevas_lineas.append(linea)

    contenido_mod = "\n".join(nuevas_lineas) + "\n"

    # GAFF005 / 0x5003h: Guardas de inclusión en .h
    if ruta.suffix.lower() in (".h", ".hpp"):
        tiene_pragma = "#pragma once" in contenido_mod
        tiene_ifndef = bool(re.search(r"#ifndef\s+\w+", contenido_mod) and re.search(r"#define\s+\w+", contenido_mod))
        if not (tiene_pragma or tiene_ifndef):
            guard_name = f"{ruta.stem.upper()}_H"
            contenido_mod = f"#ifndef {guard_name}\n#define {guard_name}\n\n{contenido_mod.strip()}\n\n#endif // {guard_name}\n"
            arreglos += 1


    # GAFF018 / 0x2003h: Autofix de esqueleto de documentación Doxygen para funciones no documentadas
    lineas_actuales = contenido_mod.splitlines()
    codigo_sin_coments = _eliminar_comentarios(contenido_mod)

    pattern_fn = (
        r"^([ \t]*)(?!(?:typedef|return)\b)((?:(?:static|inline|extern|const)[ \t]+)*(?:struct[ \t]+\w+|enum[ \t]+\w+|union[ \t]+\w+|"
        + TIPOS_BASICOS
        + r"|[a-zA-Z_]\w*)[ \t]*(\*+[ \t]*|[ \t]+\*?))([a-zA-Z_]\w*)[ \t]*\(([\s\S]*?)\)[ \t]*([;{])?"
    )
    re_fn_fix = re.compile(pattern_fn, re.MULTILINE)

    inserciones: List[Tuple[int, str]] = []
    prototipos_doc: Set[str] = set()
    if not ruta.suffix.lower() in (".h", ".hpp"):
        comp_h = ruta.with_suffix(".h")
        if comp_h.is_file():
            try:
                txt_h = comp_h.read_text(encoding="utf-8", errors="replace")
                lines_h = txt_h.splitlines()
                code_h = _eliminar_comentarios(txt_h)
                for m_ph in re_fn_fix.finditer(code_h):
                    nom = m_ph.group(4)
                    l_i = code_h[:m_ph.start()].count("\n")
                    if _tiene_comentario_documentacion(lines_h, l_i):
                        prototipos_doc.add(nom)
            except Exception:
                pass

    for m_fn in re_fn_fix.finditer(codigo_sin_coments):
        indent = m_fn.group(1)
        ret_type = m_fn.group(2)
        fn_name = m_fn.group(4)
        params_str = m_fn.group(5)
        char_cierre = m_fn.group(6)

        if fn_name in ("if", "for", "while", "switch", "return", "sizeof", "main"):
            continue

        pos_despues = m_fn.end()
        if char_cierre == ";":
            es_proto = True
        elif char_cierre == "{":
            es_proto = False
        else:
            resto = codigo_sin_coments[pos_despues:pos_despues + 100].lstrip()
            if resto.startswith(";"):
                es_proto = True
            elif resto.startswith("{") or "{" in resto[:60]:
                es_proto = False
            else:
                continue

        line_idx_start = codigo_sin_coments[:m_fn.start()].count("\n")
        if _tiene_comentario_documentacion(lineas_actuales, line_idx_start):
            prototipos_doc.add(fn_name)
            continue

        if not es_proto and fn_name in prototipos_doc:
            continue

        lineas_doc = [f"{indent}/**", f"{indent} * @brief Descripción de la función {fn_name}."]

        raw_params = [p.strip() for p in params_str.split(",") if p.strip()]
        if raw_params and not (len(raw_params) == 1 and raw_params[0] == "void"):
            lineas_doc.append(f"{indent} *")
            for p in raw_params:
                m_arg = re.search(r"([a-zA-Z_]\w*)\s*(?:\[[^\]]*\])?$", p)
                arg_name = m_arg.group(1) if m_arg else "param"
                lineas_doc.append(f"{indent} * @param {arg_name} Descripción del parámetro {arg_name}.")

        ret_clean = ret_type.strip()
        es_void = ret_clean == "void" or ret_clean.endswith(" void") or ret_clean.endswith("\tvoid")
        if not es_void:
            lineas_doc.append(f"{indent} * @return Descripción del valor de retorno.")

        lineas_doc.append(f"{indent} */")
        texto_doc = "\n".join(lineas_doc)

        inserciones.append((line_idx_start, texto_doc))
        prototipos_doc.add(fn_name)

    if inserciones:
        for l_idx, doc_block in sorted(inserciones, key=lambda x: x[0], reverse=True):
            lineas_actuales.insert(l_idx, doc_block)
            arreglos += 1
        contenido_mod = "\n".join(lineas_actuales) + "\n"

    ruta.write_text(contenido_mod, encoding="utf-8")

    # GAFF017 / 0x000Bh: Autoformato con estilo Allman mediante clang-format si está disponible
    allman_style = (
        "{BasedOnStyle: LLVM, BreakBeforeBraces: Allman, "
        "AllowShortIfStatementsOnASingleLine: false, AllowShortBlocksOnASingleLine: false, "
        "AllowShortLoopsOnASingleLine: false, AllowShortFunctionsOnASingleLine: None, "
        "IndentWidth: 4, TabWidth: 4, UseTab: Never, IndentCaseLabels: true, "
        "ColumnLimit: 80, SpaceBeforeParens: ControlStatements, PointerAlignment: Right}"
    )
    try:
        res = subprocess.run(
            ["clang-format", "-i", f"-style={allman_style}", str(ruta)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5,
        )
        if res.returncode == 0:
            arreglos += 1
    except Exception:
        # Fallback a reemplazo simple de llaves Allman
        pass

    return arreglos


def ejecutar_linter(
    rutas: List[Path] | Sequence[Path | str],
    fix: bool = False,
    reglas_excluidas: Optional[Set[str]] = None,
    reglas_habilitadas: Optional[Set[str]] = None,
    recursive: bool = False,
    config: Optional[Dict[str, Any]] = None,
) -> ReporteLinting:
    """Ejecuta el linter sobre un conjunto de archivos o directorios aplicando configuración por exclusión."""
    from gaff.core.config import cargar_configuracion_gaff

    if reglas_excluidas is None:
        dir_base = None
        for r in rutas:
            p = Path(r)
            if p.is_dir():
                dir_base = p
                break
            elif p.is_file():
                dir_base = p.parent
                break
        cfg = config or cargar_configuracion_gaff(dir_base)
        excl_cfg = cfg.get("excluded_rules", []) or cfg.get("disabled_rules", [])
        if excl_cfg:
            reglas_excluidas = set(str(x) for x in excl_cfg)

    archivos_objetivo: Set[Path] = set()
    for r in rutas:
        p = Path(r)
        if p.is_file() and p.suffix.lower() in (".c", ".h", ".cpp", ".hpp"):
            archivos_objetivo.add(p)
        elif p.is_dir():
            iterador = p.rglob("*") if recursive else p.glob("*")
            for sub_p in iterador:
                if sub_p.is_file() and sub_p.suffix.lower() in (".c", ".h", ".cpp", ".hpp"):
                    archivos_objetivo.add(sub_p)

    reportes: List[ReporteArchivo] = []
    for arch in sorted(archivos_objetivo):
        arreglos = 0
        if fix:
            arreglos = aplicar_autofix_archivo(arch)
        viols = analizar_archivo(
            arch,
            reglas_excluidas=reglas_excluidas,
            reglas_habilitadas=reglas_habilitadas,
        )
        reportes.append(ReporteArchivo(
            archivo=arch,
            violaciones=viols,
            arreglos_aplicados=arreglos,
        ))

    return ReporteLinting(archivos=reportes)
