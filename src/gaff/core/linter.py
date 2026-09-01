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
                    es_autofixable=False,
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
                    es_autofixable=False,
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
                    es_autofixable=False,
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
