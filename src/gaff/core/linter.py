"""Motor de análisis estático y autofix para GAFF con verificación exhaustiva de reglas de cátedra."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import List, Optional, Set, Tuple

from gaff.core.contexto import (
    ContextoAnalisis,
    eliminar_comentarios,
    enmascarar_literales,
    normalizar_activas,
    normalizar_exclusiones,
)
from gaff.core.models import ReporteArchivo, ReporteLinting, RuleCode, ViolacionRegla
from gaff.core.rules import CATALOGO_REGLAS, MAPA_INVERSO, MAPA_RENUMERACION, normalizar_codigo
from gaff.rules import ejecutar_todas_las_familias


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
    codigo_sin_comentarios = eliminar_comentarios(contenido_original)
    lineas_sin_comentarios = codigo_sin_comentarios.splitlines()

    codigo_sin_cadenas = enmascarar_literales(codigo_sin_comentarios)
    lineas_sin_cadenas = codigo_sin_cadenas.splitlines()

    es_header = ruta.suffix.lower() in (".h", ".hpp")

    # 1-2. Normalizar reglas excluidas/activas y construir el contexto compartido
    excluidas_norm = normalizar_exclusiones(reglas_excluidas)
    reglas_norm = normalizar_activas(reglas_habilitadas, excluidas_norm)

    ctx = ContextoAnalisis(
        ruta=ruta,
        contenido_original=contenido_original,
        lineas=lineas,
        codigo_sin_comentarios=codigo_sin_comentarios,
        lineas_sin_comentarios=lineas_sin_comentarios,
        codigo_sin_cadenas=codigo_sin_cadenas,
        lineas_sin_cadenas=lineas_sin_cadenas,
        es_header=es_header,
        excluidas_norm=excluidas_norm,
        reglas_norm=reglas_norm,
    )

    # Directivas de supresión // gaff:ignore <regla> <justificación>
    lineas_ignoradas: Dict[int, Set[str]] = {}
    re_ignore = re.compile(r"(?://|/\*)\s*gaff:ignore\s+(0x[0-9a-fA-F]+h?|all)\s+(\S.{3,})")
    for idx_l, linea_raw in enumerate(lineas):
        m_ig = re_ignore.search(linea_raw)
        if m_ig:
            cod_ig = m_ig.group(1).lower()
            if not cod_ig.endswith("h") and cod_ig.startswith("0x"):
                cod_ig += "h"
            cod_norm = normalizar_codigo(cod_ig).lower()
            cod_ant = MAPA_INVERSO.get(cod_norm, "").lower()
            cods_a_ignorar = {cod_ig, cod_norm}
            if cod_ant:
                cods_a_ignorar.add(cod_ant)
            for c in list(cods_a_ignorar):
                if c.endswith("h"):
                    cods_a_ignorar.add(c[:-1])
            lineas_ignoradas.setdefault(idx_l + 1, set()).update(cods_a_ignorar)
            if linea_raw.strip().startswith("//") or linea_raw.strip().startswith("/*"):
                lineas_ignoradas.setdefault(idx_l + 2, set()).update(cods_a_ignorar)


    # Ejecución modular de reglas por familias (Fase P1)
    violaciones = ejecutar_todas_las_familias(ctx)

    # Filtrar violaciones suprimidas por directivas // gaff:ignore <regla> <justificación>
    def _esta_suprimida(v: ViolacionRegla) -> bool:
        cod = str(v.codigo).lower()
        regs = lineas_ignoradas.get(v.linea, set())
        if "all" in regs or cod in regs:
            return True
        if cod.endswith("h") and cod[:-1] in regs:
            return True
        cod_ant = getattr(v.codigo, "codigo_anterior", "").lower()
        if cod_ant and (cod_ant in regs or (cod_ant.endswith("h") and cod_ant[:-1] in regs)):
            return True
        return False

    violaciones = [v for v in violaciones if not _esta_suprimida(v)]

    violaciones.sort(key=lambda v: (v.linea, v.columna))
    return violaciones


def _enmascarar_linea_autofix(linea: str) -> Tuple[str, Dict[str, str]]:
    """Enmascara literales de cadena, caracteres y comentarios para protegerlos durante el autofix."""
    placeholders: Dict[str, str] = {}
    contador = 0

    if linea.strip().startswith("#include"):
        return linea, placeholders

    pattern = re.compile(r'/\*.*?\*/|//.*$|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'')

    def repl(m: re.Match) -> str:
        nonlocal contador
        token = m.group(0)
        ph = f"___GAFF_MASK_{contador}___"
        contador += 1
        placeholders[ph] = token
        return ph

    linea_enmascarada = pattern.sub(repl, linea)
    return linea_enmascarada, placeholders


def _desenmascarar_linea_autofix(linea: str, placeholders: Dict[str, str]) -> str:
    """Restaura los literales de cadena, caracteres y comentarios previamente enmascarados."""
    for ph, token in placeholders.items():
        linea = linea.replace(ph, token)
    return linea


def aplicar_autofix_archivo(
    ruta: Path,
    reglas_excluidas: Optional[Set[str]] = None,
    reglas_habilitadas: Optional[Set[str]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> int:
    """Aplica correcciones automáticas sobre reglas autofixables respetando exclusiones y protegiendo literales."""
    if not ruta.is_file():
        return 0

    if config is None and reglas_excluidas is None:
        try:
            from gaff.core.config import cargar_configuracion_gaff
            cfg = cargar_configuracion_gaff(ruta.parent)
            excl_cfg = cfg.get("excluded_rules", []) or cfg.get("disabled_rules", [])
            if excl_cfg:
                reglas_excluidas = set(str(x) for x in excl_cfg)
        except Exception:
            pass

    excluidas_norm = normalizar_exclusiones(reglas_excluidas)
    reglas_norm = normalizar_activas(reglas_habilitadas, excluidas_norm)

    def _activa(cod: str) -> bool:
        cod_low = cod.lower()
        cod_nuevo = MAPA_RENUMERACION.get(cod, MAPA_RENUMERACION.get(cod_low, "")).lower()
        cod_ant = MAPA_INVERSO.get(cod, MAPA_INVERSO.get(cod_low, "")).lower()
        for c in (cod_low, cod_nuevo, cod_ant):
            if not c:
                continue
            if c in excluidas_norm or (c.endswith("h") and c[:-1] in excluidas_norm) or (not c.endswith("h") and (c + "h") in excluidas_norm):
                return False
        if reglas_habilitadas is not None:
            for c in (cod_low, cod_nuevo, cod_ant):
                if not c:
                    continue
                if c in reglas_norm or (c.endswith("h") and c[:-1] in reglas_norm) or (not c.endswith("h") and (c + "h") in reglas_norm):
                    return True
            return False
        return True

    encoding_detectado = "utf-8"
    try:
        contenido = ruta.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        contenido = ruta.read_text(encoding="latin-1")
        encoding_detectado = "latin-1"

    arreglos = 0
    lineas = contenido.splitlines()

    # GAFF020 / 0x200Eh: Autofix de fn() a fn(void)
    if _activa("0x200Eh") or _activa("0x200Dh"):
        re_empty_paren_fix = re.compile(rf"\b({TIPOS_BASICOS})\s+([a-zA-Z_]\w*)\s*\(\s*\)")
        lineas_paren_fix = []
        for l in lineas:
            if not l.strip().startswith("#"):
                l_fix, n_rep = re_empty_paren_fix.subn(r"\1 \2(void)", l)
                if n_rep > 0:
                    arreglos += n_rep
                    l = l_fix
            lineas_paren_fix.append(l)
        lineas = lineas_paren_fix

    # GAFF019 / 0x5007h: Deduplicación de #include redundantes
    if _activa("0x5007h") or _activa("0x5008h"):
        headers_vistos_fix = set()
        lineas_dedup = []
        for l in lineas:
            m_inc = re.match(r"^[ \t]*#include[ \t]+([<\"].+[>\"])", l)
            if m_inc:
                h_nom = m_inc.group(1)
                if h_nom in headers_vistos_fix:
                    arreglos += 1
                    continue
                headers_vistos_fix.add(h_nom)
            lineas_dedup.append(l)
        lineas = lineas_dedup

    nuevas_lineas = []

    re_kw = re.compile(r"\b(if|for|while|switch)\(")
    re_ptr_fix = re.compile(rf"\b({TIPOS_BASICOS})\*\s+([a-zA-Z_]\w*)")

    act_indent = _activa("0x0004h") or _activa("0x0005h")
    act_kw = _activa("0x0011h") or _activa("0x0022h") or _activa("0x0004h")
    act_ptr = _activa("0x0009h") or _activa("0x0017h") or _activa("0x0006h")
    act_semi = _activa("0x000Ah") or _activa("0x0019h")
    act_arrow = _activa("0x000Bh") or _activa("0x001Ah")
    act_unary = _activa("0x000Ch") or _activa("0x001Bh")
    act_comma = _activa("0x000Dh") or _activa("0x001Ch") or _activa("0x002Bh")
    act_paren = _activa("0x000Eh") or _activa("0x001Dh")
    act_spaces = _activa("0x000Fh") or _activa("0x001Eh")
    act_ret_paren = _activa("0x200Fh") or _activa("0x2010h")
    act_yoda = _activa("0x100Bh") or _activa("0x100Ch")
    act_ternary = _activa("0x100Ch") or _activa("0x100Eh")
    act_const = _activa("0x3017h")
    act_cast = _activa("0x301Bh") or _activa("0x100Dh")
    act_double_ptr = _activa("0x0017h")
    act_memset = _activa("0x3016h")
    act_scalar = _activa("0x0010h") or _activa("0x001Fh")
    act_chained = _activa("0x1010h") or _activa("0x1012h")
    act_main = _activa("0x2012h") or _activa("0x2013h")
    act_macro = _activa("0x5013h") or _activa("0x5015h")

    for linea in lineas:
        orig = linea
        # Enmascarar literales de cadena, caracteres y comentarios para protegerlos de corrupción
        linea, placeholders = _enmascarar_linea_autofix(linea)

        # GAFF010 / 0x0005h: tabs to spaces y strip trailing
        if act_indent:
            linea = linea.replace("\t", "    ").rstrip()
            stripped = linea.strip()
            if stripped and not linea.lstrip().startswith(("*", "/*")):
                lead = len(linea) - len(linea.lstrip(" "))
                if lead > 0 and lead % 4 != 0:
                    nuevo_lead = max(4, ((lead + 2) // 4) * 4)
                    linea = (" " * nuevo_lead) + linea.lstrip(" ")

        # GAFF007 / 0x0004h: keywords spacing
        if act_kw:
            linea = re_kw.sub(r"\1 (", linea)

        # GAFF014 / 0x0006h: pointer asterisk spacing
        if act_ptr and not linea.strip().startswith("#"):
            linea = re_ptr_fix.sub(r"\1 *\2", linea)

        # GAFF / 0x0019h: Espacios antes de ; y ,
        if act_semi and not linea.strip().startswith("#") and not linea.strip().startswith("/*") and not linea.strip().startswith("*"):
            linea = re.sub(r"[ \t]+([;,])", r"\1", linea)

        # GAFF / 0x001Ah: Miembros -> y .
        if act_arrow:
            linea = re.sub(r'([a-zA-Z0-9_]+)[ \t]+->[ \t]*([a-zA-Z0-9_]+)', r'\1->\2', linea)
            linea = re.sub(r'([a-zA-Z0-9_]+)[ \t]*->[ \t]+([a-zA-Z0-9_]+)', r'\1->\2', linea)
            linea = re.sub(r'([a-zA-Z_]\w*)[ \t]+\.[ \t]*([a-zA-Z_]\w*)', r'\1.\2', linea)
            linea = re.sub(r'([a-zA-Z_]\w*)[ \t]*\.[ \t]+([a-zA-Z_]\w*)', r'\1.\2', linea)

        # GAFF / 0x001Bh: Unarios ++, --, !
        if act_unary:
            linea = re.sub(r'\b([a-zA-Z_]\w*)[ \t]+(\+\+|\-\-)', r'\1\2', linea)
            linea = re.sub(r'(\+\+|\-\-)[ \t]+([a-zA-Z_]\w*)', r'\1\2', linea)
            linea = re.sub(r'(!)(?!=)[ \t]+([a-zA-Z_]\w*)', r'\1\2', linea)

        # GAFF / 0x001Ch: Espacio tras coma
        if act_comma:
            linea = re.sub(r',(?=[^\s\n\r/>])', r', ', linea)

        # GAFF / 0x001Dh: Espacio interno en paréntesis
        if act_paren:
            linea = re.sub(r'\([ \t]+(?!\s|\))', r'(', linea)
            linea = re.sub(r'(?<!\s|\()[ \t]+\)', r')', linea)

        # GAFF / 0x001Eh: Colapsar espacios múltiples intra-línea
        if act_spaces and not linea.strip().startswith("#") and not linea.strip().startswith("/*") and not linea.strip().startswith("*"):
            indent = len(linea) - len(linea.lstrip())
            linea = linea[:indent] + re.sub(r'(?<=\S)[ \t]{2,}(?=\S)', ' ', linea[indent:])

        # 0x2010h: return (x); -> return x;
        if act_ret_paren:
            m_ret = re.match(r"^([ \t]*return)\s*\(\s*([a-zA-Z_]\w*(?:->\w+|\.\w+|\[[^\]]+\])?|\d+|NULL)\s*\)\s*;", linea)
            if m_ret:
                linea = f"{m_ret.group(1)} {m_ret.group(2)};"

        # 0x100Ch: Yoda condition NULL == ptr -> ptr == NULL
        if act_yoda:
            linea = re.sub(r"\b(NULL|0|[1-9]\d*|true|false)\s*(==|!=)\s*([a-zA-Z_]\w*(?:->\w+|\.\w+|\[[^\]]+\])?)", r"\3 \2 \1", linea)

        # 0x100Eh: Operador ternario ? : con espaciado
        if act_ternary and "?" in linea and ":" in linea and not ("case " in linea or "default:" in linea):
            linea = re.sub(r"(\S)\s*\?\s*(\S)", r"\1 ? \2", linea)
            linea = re.sub(r"(\S)\s*:\s*(\S)", r"\1 : \2", linea)

        # 0x3017h: int const -> const int
        if act_const:
            linea = re.sub(rf"\b({TIPOS_BASICOS})\s+const\b", r"const \1", linea)

        # 0x100Dh: cast innecesario de literal (int)0 -> 0
        if act_cast:
            linea = re.sub(r"\((?:int|char|long|float|double|size_t)\)\s*(\(?\b\d+(?:\.\d+)?f?\b\)?|\((?:int|char|long|float|double|size_t)\))", r"\1", linea)

        # 0x0017h: doble puntero tipo **var
        if act_double_ptr:
            linea = re.sub(rf"\b({TIPOS_BASICOS})\s*(\*(?:\s*\*|\s+\*))\s*([a-zA-Z_]\w*)", r"\1 **\3", linea)

        # 0x3016h: memset(ptr, sizeof(ptr), 0) -> memset(ptr, 0, sizeof(ptr))
        if act_memset:
            re_ms_fix = re.compile(r"\bmemset\s*\(\s*([^,]+?)\s*,\s*(sizeof\([^)]+\)|\d+|[a-zA-Z_]\w*)\s*,\s*(0|'\\0'|NULL)\s*\)")
            linea = re_ms_fix.sub(r"memset(\1, \3, \2)", linea)

        # 0x001Fh: int x = {0}; -> int x = 0;
        if act_scalar and not ("[" in linea or "struct " in linea or "union " in linea):
            re_scalar_fix = re.compile(rf"^([ \t]*(?!(?:struct|union)\b)(?:const\s+)?(?:static\s+)?{TIPOS_BASICOS}\s+\*?\s*[a-zA-Z_]\w*\s*=\s*)\{{\s*([^,{{}}\n]+?)\s*\}}(\s*;)")
            linea = re_scalar_fix.sub(r"\1\2\3", linea)

        # 0x1012h: a < b < c -> a < b && b < c
        if act_chained and not ("<<" in linea or ">>" in linea or linea.strip().startswith("#")):
            re_chained_fix = re.compile(r"(?<![<>=!])\b([a-zA-Z0-9_]+)\s*(<=|<|>=|>|==)\s*([a-zA-Z0-9_]+)\s*(<=|<|>=|>|==)\s*([a-zA-Z0-9_]+)\b(?![<>=])")
            linea = re_chained_fix.sub(r"\1 \2 \3 && \3 \4 \5", linea)

        # 0x2013h: void main( -> int main(
        if act_main and re.match(r"^[ \t]*void\s+main\s*\(", linea):
            linea = re.sub(r"^([ \t]*)void(\s+main\s*\()", r"\1int\2", linea)

        # 0x5015h: #define TAM 10 + 5 -> #define TAM (10 + 5)
        if act_macro:
            m_macro_fix = re.match(r"^([ \t]*#\s*define\s+[a-zA-Z_]\w*(?:\([^)]*\))?[ \t]+)(.+)$", linea)
            if m_macro_fix:
                b_fix = m_macro_fix.group(2).strip()
                if not (b_fix.startswith("(") and b_fix.endswith(")")) and re.search(r"[\+\-\*/%&|\^]|<<|>>|&&|\|\||\?", b_fix):
                    if not re.match(r"^(?:0x[0-9a-fA-F]+|\d+(?:\.\d+)?f?|[a-zA-Z_]\w*)$", b_fix):
                        linea = f"{m_macro_fix.group(1)}({b_fix})"

        # 0x0022h: if( -> if (
        if act_kw and not (linea.strip().startswith("//") or linea.strip().startswith("/*") or linea.strip().startswith("#")):
            linea = re.sub(r"\b(if|for|while|switch)\(", r"\1 (", linea)

        # 0x002Bh: f(a,b) -> f(a, b) y f(a , b) -> f(a, b)
        if act_comma and not (linea.strip().startswith("//") or linea.strip().startswith("/*") or linea.strip().startswith("#")):
            linea = re.sub(r"\s+,", ",", linea)
            linea = re.sub(r",([^\s\)\],])", r", \1", linea)

        # Restaurar literales y comentarios protegidos
        linea = _desenmascarar_linea_autofix(linea, placeholders)

        if linea != orig:
            arreglos += 1
        nuevas_lineas.append(linea)

    contenido_mod = "\n".join(nuevas_lineas) + "\n"

    # GAFF005 / 0x5003h: Guardas de inclusión en .h
    if (_activa("0x5002h") or _activa("0x5003h")) and ruta.suffix.lower() in (".h", ".hpp"):
        tiene_pragma = "#pragma once" in contenido_mod
        tiene_ifndef = bool(re.search(r"#ifndef\s+\w+", contenido_mod) and re.search(r"#define\s+\w+", contenido_mod))
        if not (tiene_pragma or tiene_ifndef):
            guard_name = f"{ruta.stem.upper()}_H"
            contenido_mod = f"#ifndef {guard_name}\n#define {guard_name}\n\n{contenido_mod.strip()}\n\n#endif // {guard_name}\n"
            arreglos += 1


    # GAFF018 / 0x2003h: Autofix de esqueleto de documentación Doxygen para funciones no documentadas
    if _activa("0x2003h"):
        lineas_actuales = contenido_mod.splitlines()
        codigo_sin_coments = eliminar_comentarios(contenido_mod)

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
                    code_h = eliminar_comentarios(txt_h)
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

    if not contenido.endswith("\n"):
        arreglos += 1
    if not contenido_mod.endswith("\n"):
        contenido_mod += "\n"

    if contenido_mod != contenido:
        ruta.write_text(contenido_mod, encoding=encoding_detectado)

    # GAFF017 / 0x000Bh: Autoformato con estilo Allman mediante clang-format si está disponible
    if _activa("0x0007h") or _activa("0x000Bh"):
        allman_style = (
            "{BasedOnStyle: LLVM, BreakBeforeBraces: Allman, "
            "AllowShortIfStatementsOnASingleLine: false, AllowShortBlocksOnASingleLine: false, "
            "AllowShortLoopsOnASingleLine: false, AllowShortFunctionsOnASingleLine: None, "
            "IndentWidth: 4, TabWidth: 4, UseTab: Never, IndentCaseLabels: true, "
            "ColumnLimit: 80, SpaceBeforeParens: ControlStatements, PointerAlignment: Right}"
        )
        try:
            contenido_pre = ruta.read_text(encoding=encoding_detectado, errors="replace") if ruta.exists() else ""
            res = subprocess.run(
                ["clang-format", "-i", f"-style={allman_style}", str(ruta)],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5,
            )
            if res.returncode == 0:
                contenido_post = ruta.read_text(encoding=encoding_detectado, errors="replace")
                if contenido_post != contenido_pre:
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
            arreglos = aplicar_autofix_archivo(
                arch,
                reglas_excluidas=reglas_excluidas,
                reglas_habilitadas=reglas_habilitadas,
                config=config,
            )
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


def convertir_pragma_once_a_guardas(contenido: str, stem: str) -> Tuple[str, bool]:
    """Convierte directivas #pragma once en guardas #ifndef __STEM_H__ canónicas."""
    if not re.search(r"^[ \t]*#pragma\s+once\b", contenido, re.MULTILINE):
        return contenido, False
    stem_clean = re.sub(r"[^A-Za-z0-9_]", "_", stem).upper()
    guard_name = f"__{stem_clean}_H__"
    nuevo_contenido = re.sub(r"^[ \t]*#pragma\s+once[ \t]*\n?", "", contenido, flags=re.MULTILINE)
    resultado = f"#ifndef {guard_name}\n#define {guard_name}\n\n{nuevo_contenido.strip()}\n\n#endif // {guard_name}\n"
    return resultado, True


def detectar_inclusiones_ciclicas(rutas: List[Path]) -> List[Tuple[str, str]]:
    """Detecta ciclos de inclusión mutua directa entre archivos de cabecera del proyecto."""
    grafo: Dict[str, Set[str]] = {}
    for r in rutas:
        p = Path(r)
        if not p.is_file() or p.suffix.lower() not in (".h", ".hpp"):
            continue
        try:
            txt = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        includes = set(re.findall(r'^[ \t]*#include\s+"([^"]+)"', txt, re.MULTILINE))
        grafo[p.name] = includes

    ciclos = []
    for header, incls in grafo.items():
        for inc in incls:
            inc_name = Path(inc).name
            if inc_name in grafo and header in grafo[inc_name]:
                par = tuple(sorted([header, inc_name]))
                if par not in ciclos:
                    ciclos.append(par)
    return ciclos


def auditar_guardas_proyecto(rutas: List[Path]) -> List[Dict[str, Any]]:
    """Detecta colisiones de nombres de macros de guarda entre diferentes archivos .h."""
    guardas: Dict[str, List[Path]] = {}
    for r in rutas:
        p = Path(r)
        if not p.is_file() or p.suffix.lower() not in (".h", ".hpp"):
            continue
        try:
            txt = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        m = re.search(r"^[ \t]*#ifndef\s+(\w+)", txt, re.MULTILINE)
        if m:
            gname = m.group(1)
            guardas.setdefault(gname, []).append(p)

    colisiones = []
    for gname, paths in guardas.items():
        if len(paths) > 1:
            colisiones.append({
                "guarda": gname,
                "archivos": [str(p) for p in paths]
            })
    return colisiones
