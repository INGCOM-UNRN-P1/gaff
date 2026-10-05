"""Reglas de estilo de cátedra — Estructuras de control y flujo (rules_50xx)."""

from __future__ import annotations

import re
from typing import List

from gaff.core.contexto import (
    ContextoAnalisis,
)
from gaff.core.models import ViolacionRegla


# 0x10XXh: Estructuras de Control y Lazos
# 0x1006h: Prohibición de goto
def _regla_1006(ctx: ContextoAnalisis, violaciones: List[ViolacionRegla]) -> None:
    ruta = ctx.ruta
    lineas = ctx.lineas
    lineas_sin_comentarios = ctx.lineas_sin_comentarios
    if ctx.esta_activa("0x1006h"):
        for idx, linea in enumerate(lineas_sin_comentarios, 1):
            m_goto = re.search(r"\bgoto\s+\w+", linea)
            if m_goto:
                rcode, tit = ctx.regla_info("0x1006h")
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
def _regla_1002(ctx: ContextoAnalisis, violaciones: List[ViolacionRegla]) -> None:
    ruta = ctx.ruta
    lineas = ctx.lineas
    lineas_sin_comentarios = ctx.lineas_sin_comentarios
    if ctx.esta_activa("0x1002h"):
        for idx, linea in enumerate(lineas_sin_comentarios, 1):
            m_cont = re.search(r"\bcontinue\s*;", linea)
            if m_cont:
                rcode, tit = ctx.regla_info("0x1002h")
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
def _regla_1007(ctx: ContextoAnalisis, violaciones: List[ViolacionRegla]) -> None:
    ruta = ctx.ruta
    lineas = ctx.lineas
    lineas_sin_comentarios = ctx.lineas_sin_comentarios
    if ctx.esta_activa("0x1007h"):
        for idx, linea in enumerate(lineas_sin_comentarios, 1):
            if not linea.strip().startswith("#"):
                m_tern = re.search(r"(?<=\w|\))\s*\?\s*[^:]+\s*:\s*", linea)
                if m_tern:
                    rcode, tit = ctx.regla_info("0x1007h")
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


# 0x1008h: Switch sin default
def _regla_1008(ctx: ContextoAnalisis, violaciones: List[ViolacionRegla]) -> None:
    ruta = ctx.ruta
    codigo_sin_comentarios = ctx.codigo_sin_comentarios
    if ctx.esta_activa("0x1008h"):
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
                rcode, tit = ctx.regla_info("0x1008h")
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
def _regla_1003(ctx: ContextoAnalisis, violaciones: List[ViolacionRegla]) -> None:
    ruta = ctx.ruta
    lineas = ctx.lineas
    lineas_sin_comentarios = ctx.lineas_sin_comentarios
    if ctx.esta_activa("0x1003h"):
        re_for_empty = re.compile(r"\bfor\s*\(\s*;\s*;\s*\)|\bfor\s*\(\s*;\s*[^;]+;\s*\)")
        for idx, linea in enumerate(lineas_sin_comentarios, 1):
            m_linea = re_for_empty.search(linea)
            if m_linea:
                rcode, tit = ctx.regla_info("0x1003h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=idx,
                    columna=m_linea.start() + 1,
                    mensaje="Uso de 'for' como lazo puramente lógico o indefinido.",
                    sugerencia="Utilizá 'while' para lazos condicionales y reservá 'for' para conteo definido.",
                    codigo_linea=lineas[idx - 1],
                    es_autofixable=False,
                ))


# 0x1004h: Condiciones complejas deben simplificarse o comentarse
def _regla_1004(ctx: ContextoAnalisis, violaciones: List[ViolacionRegla]) -> None:
    ruta = ctx.ruta
    lineas = ctx.lineas
    codigo_sin_comentarios = ctx.codigo_sin_comentarios
    contenido_original = ctx.contenido_original
    if ctx.esta_activa("0x1004h"):
        re_control_cond = re.compile(r"\b(?:if|while)\s*\((.*?)\)\s*\{?", re.DOTALL)
        for m in re_control_cond.finditer(codigo_sin_comentarios):
            cond_texto = m.group(1)
            total_ops = len(re.findall(r"&&", cond_texto)) + len(re.findall(r"\|\|", cond_texto))
            if total_ops >= 3:
                linea_num = contenido_original[:m.start()].count("\n") + 1
                rcode, tit = ctx.regla_info("0x1004h")
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


# 0x1005h: Evitar condiciones ambiguas por truthiness (strcmp, punteros, chars)
def _regla_1005(ctx: ContextoAnalisis, violaciones: List[ViolacionRegla]) -> None:
    ruta = ctx.ruta
    lineas = ctx.lineas
    lineas_sin_comentarios = ctx.lineas_sin_comentarios
    if ctx.esta_activa("0x1005h"):
        re_not_strcmp = re.compile(r"\b(?:if|while)\s*\(\s*!\s*str(?:n)?(?:case)?cmp\s*\(")
        re_not_ptr = re.compile(r"\b(?:if|while)\s*\(\s*!\s*([a-zA-Z_]\w*(?:_ptr|ptr|p))\s*\)")
        re_not_char = re.compile(r"\b(?:if|while)\s*\(\s*!\s*([a-zA-Z_]\w*\[[^\]]+\])\s*\)")

        for i, l in enumerate(lineas_sin_comentarios):
            m1 = re_not_strcmp.search(l)
            if m1:
                rcode, tit = ctx.regla_info("0x1005h")
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
                rcode, tit = ctx.regla_info("0x1005h")
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
                rcode, tit = ctx.regla_info("0x1005h")
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


# 0x100Ah: Prohibición de asignaciones simples dentro de condiciones lógicas
def _regla_1009(ctx: ContextoAnalisis, violaciones: List[ViolacionRegla]) -> None:
    ruta = ctx.ruta
    lineas = ctx.lineas
    lineas_sin_comentarios = ctx.lineas_sin_comentarios
    if ctx.esta_activa("0x1009h"):
        re_assign_in_cond = re.compile(r"\b(?:if|while)\s*\(\s*([a-zA-Z_]\w*)\s*=\s*([^=;()]+)\s*\)")
        for i, l in enumerate(lineas_sin_comentarios):
            m_as = re_assign_in_cond.search(l)
            if m_as:
                var_nom = m_as.group(1)
                val_expr = m_as.group(2).strip()
                rcode, tit = ctx.regla_info("0x1009h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_as.start() + 1,
                    mensaje=f"Asignación simple '=' dentro de condición lógica: 'if ({var_nom} = {val_expr})'. ¿Quisiste usar '=='?",
                    sugerencia=f"Cambiá a comparación de igualdad 'if ({var_nom} == {val_expr})' o extraé la asignación antes del condicional.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))


# 0x100Eh: Prohibición de condiciones constantes o tautológicas en sentencias if
def _regla_100c(ctx: ContextoAnalisis, violaciones: List[ViolacionRegla]) -> None:
    ruta = ctx.ruta
    lineas = ctx.lineas
    lineas_sin_comentarios = ctx.lineas_sin_comentarios
    if ctx.esta_activa("0x100Ch"):
        re_const_if = re.compile(r"\bif\s*\(\s*(1|0|true|false)\s*\)")
        for i, l in enumerate(lineas_sin_comentarios):
            m_ci = re_const_if.search(l)
            if m_ci:
                val = m_ci.group(1)
                rcode, tit = ctx.regla_info("0x100Ch")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_ci.start() + 1,
                    mensaje=f"Condición constante tautológica 'if ({val})' detectada.",
                    sugerencia="Eliminá la rama condicional muerta o reemplazala por una expresión lógica variable.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))


# 0x100Fh: Prohibición de condiciones de parada compuestas complejas en lazos for
def _regla_100d(ctx: ContextoAnalisis, violaciones: List[ViolacionRegla]) -> None:
    ruta = ctx.ruta
    lineas = ctx.lineas
    lineas_sin_comentarios = ctx.lineas_sin_comentarios
    if ctx.esta_activa("0x100Dh"):
        re_for_complex = re.compile(r"\bfor\s*\([^;]*;([^;]*(?:&&|\|\|)[^;]*);[^)]*\)")
        for i, l in enumerate(lineas_sin_comentarios):
            m_fc = re_for_complex.search(l)
            if m_fc:
                rcode, tit = ctx.regla_info("0x100Dh")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m_fc.start() + 1,
                    mensaje="Lazo 'for' con condición de parada lógica compuesta (operadores && / ||).",
                    sugerencia="Mantené el lazo 'for' con una comprobación simple de cota; utilizá 'while' para lazos con condiciones de parada complejas.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))


# 0x1010h: Delimitación obligatoria con bloque de llaves en lazos do-while
def _regla_100e(ctx: ContextoAnalisis, violaciones: List[ViolacionRegla]) -> None:
    ruta = ctx.ruta
    lineas = ctx.lineas
    lineas_sin_comentarios = ctx.lineas_sin_comentarios
    if ctx.esta_activa("0x100Eh"):
        re_do_nok = re.compile(r"^[ \t]*do[ \t]+(?!\{)[a-zA-Z_]\w*", re.MULTILINE)
        for i, l in enumerate(lineas_sin_comentarios):
            m_dn = re_do_nok.match(l)
            if m_dn:
                rcode, tit = ctx.regla_info("0x100Eh")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=1,
                    mensaje="Lazo 'do ... while' sin bloque de llaves '{ ... }' delimitador.",
                    sugerencia="Encerrá siempre el cuerpo de 'do' entre llaves explícitas.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))


# 0x1011h: Prohibición de cláusula else redundante tras sentencia de retorno anticipado
def _regla_100f(ctx: ContextoAnalisis, violaciones: List[ViolacionRegla]) -> None:
    ruta = ctx.ruta
    lineas = ctx.lineas
    codigo_sin_comentarios = ctx.codigo_sin_comentarios
    contenido_original = ctx.contenido_original
    if ctx.esta_activa("0x100Fh"):
        re_else_ret = re.compile(r"\breturn\s*[^;]*;\s*\}\s*else\b", re.MULTILINE)
        for m_er in re_else_ret.finditer(codigo_sin_comentarios):
            linea_num = contenido_original[:m_er.start()].count("\n") + 1
            rcode, tit = ctx.regla_info("0x100Fh")
            violaciones.append(ViolacionRegla(
                codigo=rcode,
                titulo=tit,
                archivo=ruta,
                linea=linea_num,
                columna=1,
                mensaje="Cláusula 'else' redundante tras bloque finalizado incondicionalmente con 'return'.",
                sugerencia="Desanidá el bloque posterior eliminando el 'else' innecesario.",
                codigo_linea=lineas[linea_num - 1] if linea_num <= len(lineas) else "",
                es_autofixable=False,
            ))


# 0x100Eh: Espaciado obligatorio alrededor de operadores ternarios (? :)
def _regla_100c_2(ctx: ContextoAnalisis, violaciones: List[ViolacionRegla]) -> None:
    ruta = ctx.ruta
    lineas = ctx.lineas
    lineas_sin_cadenas = ctx.lineas_sin_cadenas
    if ctx.esta_activa("0x100Ch"):
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("#") or "case " in l or "default:" in l:
                continue
            if "?" in l and ":" in l:
                m_q = re.search(r"(\S\?|\?\S)", l)
                m_c = re.search(r"(\S:|:\S)", l)
                coincidencia = m_q if m_q is not None else m_c
                if coincidencia is not None:
                    pos = coincidencia.start()
                    rcode, tit = ctx.regla_info("0x100Ch")
                    violaciones.append(ViolacionRegla(
                        codigo=rcode,
                        titulo=tit,
                        archivo=ruta,
                        linea=i + 1,
                        columna=pos + 1,
                        mensaje="Falta espacio alrededor del operador ternario ('?' o ':').",
                        sugerencia="Debe haber exactamente un espacio antes y después de '?' y ':' (ej: 'cond ? a : b').",
                        codigo_linea=lineas[i],
                        es_autofixable=True,
                    ))


# 0x1012h: Prohibición de comparaciones encadenadas no idiomáticas en C (a < b < c)
def _regla_1010(ctx: ContextoAnalisis, violaciones: List[ViolacionRegla]) -> None:
    ruta = ctx.ruta
    lineas = ctx.lineas
    lineas_sin_cadenas = ctx.lineas_sin_cadenas
    if ctx.esta_activa("0x1010h"):
        re_chained_cmp = re.compile(
            r"(?<![<>=!])\b([a-zA-Z0-9_]+)\s*(<=|<|>=|>|==)\s*([a-zA-Z0-9_]+)\s*(<=|<|>=|>|==)\s*([a-zA-Z0-9_]+)\b(?![<>=])"
        )
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("#") or l.strip().startswith("//") or l.strip().startswith("/*"):
                continue
            if "<<" in l or ">>" in l:
                continue
            for m in re_chained_cmp.finditer(l):
                a_expr = m.group(1)
                op1 = m.group(2)
                b_expr = m.group(3)
                op2 = m.group(4)
                c_expr = m.group(5)
                rcode, tit = ctx.regla_info("0x1010h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=m.start() + 1,
                    mensaje=f"Comparación encadenada no idiomática '{m.group(0)}'. En C se evalúa como '({a_expr} {op1} {b_expr}) {op2} {c_expr}', lo cual produce errores de lógica.",
                    sugerencia=f"Desglosá la condición utilizando el operador lógico '&&': '{a_expr} {op1} {b_expr} && {b_expr} {op2} {c_expr}'.",
                    codigo_linea=lineas[i],
                    es_autofixable=True,
                ))


# 0x1016h: Detector de expresiones booleanas complejas sin paréntesis aclaratorios
def _regla_1013(ctx: ContextoAnalisis, violaciones: List[ViolacionRegla]) -> None:
    ruta = ctx.ruta
    lineas = ctx.lineas
    lineas_sin_cadenas = ctx.lineas_sin_cadenas
    if ctx.esta_activa("0x1013h"):
        re_if_cond = re.compile(r"\b(if|while)\s*\((.+)\)")
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("//") or l.strip().startswith("/*") or l.strip().startswith("#"):
                continue
            m_ic = re_if_cond.search(l)
            if m_ic:
                cond = m_ic.group(2)
                if "&&" in cond and "||" in cond:
                    if not re.search(r"\([^)]*?(&&|\|\|)[^)]*?\)", cond):
                        rcode, tit = ctx.regla_info("0x1013h")
                        violaciones.append(ViolacionRegla(
                            codigo=rcode,
                            titulo=tit,
                            archivo=ruta,
                            linea=i + 1,
                            columna=m_ic.start() + 1,
                            mensaje="Expresión booleana combina '&&' y '||' sin paréntesis explícitos que aclaren la precedencia pedagógica.",
                            sugerencia="Agrupá las condiciones con paréntesis para hacer explícito el orden de evaluación.",
                            codigo_linea=lineas[i],
                            es_autofixable=False,
                        ))


# 0x1017h: Detector de operadores de incremento o decremento múltiples en una misma expresión
def _regla_1014(ctx: ContextoAnalisis, violaciones: List[ViolacionRegla]) -> None:
    ruta = ctx.ruta
    lineas = ctx.lineas
    lineas_sin_cadenas = ctx.lineas_sin_cadenas
    if ctx.esta_activa("0x1014h"):
        re_multi_inc = re.compile(r"(\+\+|--)\s*([a-zA-Z_]\w*)|([a-zA-Z_]\w*)\s*(\+\+|--)")
        for i, l in enumerate(lineas_sin_cadenas):
            if l.strip().startswith("//") or l.strip().startswith("/*") or l.strip().startswith("#"):
                continue
            encontrados = []
            for m in re_multi_inc.finditer(l):
                var = m.group(2) or m.group(3)
                encontrados.append(var)
            if len(encontrados) > 1 and len(encontrados) != len(set(encontrados)):
                rep = [v for v in set(encontrados) if encontrados.count(v) > 1][0]
                rcode, tit = ctx.regla_info("0x1014h")
                violaciones.append(ViolacionRegla(
                    codigo=rcode,
                    titulo=tit,
                    archivo=ruta,
                    linea=i + 1,
                    columna=l.find(rep) + 1,
                    mensaje=f"Operaciones de incremento o decremento múltiples sobre la variable '{rep}' en una misma sentencia (comportamiento indefinido por sequence points).",
                    sugerencia="Separar los incrementos o decrementos en sentencias individuales independientes.",
                    codigo_linea=lineas[i],
                    es_autofixable=False,
                ))


# Las reglas de la familia, en el orden en que se evalúan (y se informan).
REGLAS = (
    _regla_1006,
    _regla_1002,
    _regla_1007,
    _regla_1008,
    _regla_1003,
    _regla_1004,
    _regla_1005,
    _regla_1009,
    _regla_100c,
    _regla_100d,
    _regla_100e,
    _regla_100f,
    _regla_100c_2,
    _regla_1010,
    _regla_1013,
    _regla_1014,
)


def verificar(ctx: ContextoAnalisis) -> List[ViolacionRegla]:
    """Evalúa las reglas de Estructuras de control y flujo sobre el contexto del archivo."""
    violaciones: List[ViolacionRegla] = []
    for regla in REGLAS:
        regla(ctx, violaciones)
    return violaciones
