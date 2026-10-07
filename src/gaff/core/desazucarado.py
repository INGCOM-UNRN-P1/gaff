"""Equivalencias sintácticas de C, el «desazucarado» (`gaff explain-syntax`).

Revisión 05 §3 (la propuesta `morpheus` del histórico): buena parte de la sintaxis de C es azúcar
sobre unas pocas operaciones. `a[i]` es `*(a + i)`, `p->x` es `(*p).x`, `x += y` es `x = x + (y)`,
un `for` es un `while` y un parámetro `int v[]` es un puntero. Para cada sentencia que usa alguna de
estas formas se muestra la sentencia equivalente, sin el azúcar, y qué equivalencia se aplicó.

El análisis es sintáctico (tree-sitter): no compila ni ejecuta el código.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Tuple

# tipo → (forma general, explicación)
EXPLICACIONES: Dict[str, Tuple[str, str]] = {
    "subindice": (
        "a[i] ≡ *(a + i)",
        "El subíndice es aritmética de punteros: a[i] es el elemento que está i posiciones después de "
        "donde apunta a. Por eso un arreglo se pasa a una función como un puntero (y hasta i[a] compila).",
    ),
    "flecha": (
        "p->x ≡ (*p).x",
        "La flecha accede a un campo a través de un puntero: primero se desreferencia el puntero y después "
        "se toma el campo. Los paréntesis hacen falta porque el punto tiene más precedencia que el *.",
    ),
    "asignacion_compuesta": (
        "x += y ≡ x = x + (y)",
        "La asignación compuesta opera y guarda en un paso. Una diferencia: x se evalúa una sola vez, así "
        "que en v[i++] += 1 la i se incrementa una vez y no dos.",
    ),
    "incremento": (
        "x++; ≡ x = x + 1;",
        "Como sentencia suelta, x++ y ++x hacen lo mismo. Dentro de una expresión no: x++ vale el valor "
        "anterior de x y ++x vale el nuevo.",
    ),
    "for": (
        "for (ini; cond; inc) cuerpo ≡ { ini; while (cond) { cuerpo inc; } }",
        "El for es un while con la inicialización antes y el incremento al final del cuerpo. La variable "
        "declarada en ini existe solo dentro del for (por eso las llaves de afuera) y una condición vacía "
        "es verdadera.",
    ),
    "direccion_de_elemento": (
        "&a[i] ≡ (a + i)",
        "&a[i] es la dirección del elemento i: &*(a + i), y el & deshace al *.",
    ),
    "ternario": (
        "x = c ? a : b; ≡ if (c) x = a; else x = b;",
        "El operador condicional es un if/else que produce un valor: por eso se puede usar dentro de una "
        "expresión, donde un if no entra.",
    ),
    "condicion_implicita": (
        "if (p) ≡ if (p != 0)",
        "En C, cualquier valor distinto de 0 es verdadero: con un puntero, if (p) es if (p != NULL).",
    ),
    "negacion": (
        "!x ≡ (x == 0)",
        "El ! da 1 si el valor es 0 y 0 si no: con un puntero, !p es p == NULL.",
    ),
    "cadena": (
        "char s[] = \"ok\"; ≡ char s[] = {'o', 'k', '\\0'};",
        "Una cadena literal inicializa un arreglo de char y agrega el '\\0' del final: \"ok\" ocupa 3 "
        "bytes, no 2.",
    ),
    "parametro_arreglo": (
        "void f(int v[]) ≡ void f(int *v)",
        "En un parámetro, la declaración de arreglo es un puntero: la función recibe la dirección del "
        "primer elemento, sizeof(v) da el tamaño del puntero y el largo hay que pasarlo aparte.",
    ),
}

ADVERTENCIA_CONTINUE = ("Este for tiene un continue: en el for, continue salta al incremento; en el while "
                        "equivalente saltaría directo a la condición, así que hay que repetir el incremento "
                        "antes de cada continue.")
ADVERTENCIA_INCREMENTO_EN_EXPRESION = {
    "post": "Dentro de una expresión, {a}{op} vale el valor anterior de {a} y después la modifica.",
    "pre": "Dentro de una expresión, {op}{a} modifica {a} primero y vale el valor nuevo.",
}

# Expresiones que no necesitan paréntesis al quedar como operando de + o de *.
_ATOMICAS = {"identifier", "number_literal", "char_literal", "string_literal", "call_expression",
             "subscript_expression", "field_expression", "parenthesized_expression", "update_expression",
             "sizeof_expression", "true", "false", "null"}
# Valores que, usados como condición, son una comparación implícita con 0.
_VALORES = {"identifier", "field_expression", "subscript_expression", "pointer_expression"}
_BUCLES = {"for_statement", "while_statement", "do_statement"}


@dataclass
class Equivalencia:
    tipo: str
    original: str
    equivalente: str
    advertencia: str = ""


@dataclass
class Sentencia:
    linea: int
    original: str
    equivalente: str
    equivalencias: List[Equivalencia] = field(default_factory=list)

    def a_dict(self) -> dict:
        return asdict(self)


def _parser():
    import tree_sitter_c as tsc
    from tree_sitter import Language, Parser

    return Parser(Language(tsc.language()))


class _Desazucarador:
    def __init__(self, fuente: bytes):
        self.fuente = fuente
        self.sentencias: List[Sentencia] = []
        self._equivalencias: List[Equivalencia] = []

    # Texto ----------------------------------------------------------------------------------------
    @staticmethod
    def texto(nodo) -> str:
        texto: str = nodo.text.decode("utf-8", errors="replace")
        return texto

    def _anotar(self, tipo: str, original: str, equivalente: str, advertencia: str = "") -> None:
        self._equivalencias.append(Equivalencia(tipo, original, equivalente, advertencia))

    def _operando(self, nodo, reescrito: str) -> str:
        return reescrito if nodo.type in _ATOMICAS else f"({reescrito})"

    def reescribir(self, nodo) -> str:
        """El texto de `nodo` sin azúcar, anotando cada equivalencia aplicada."""
        metodo = getattr(self, f"_r_{nodo.type}", None)
        if metodo is not None:
            resultado: Optional[str] = metodo(nodo)
            if resultado is not None:
                return resultado
        return self._generico(nodo)

    def _generico(self, nodo, reemplazos: Optional[Dict[int, str]] = None) -> str:
        """El texto original, con cada hijo reemplazado por su versión reescrita."""
        if not nodo.children:
            return self.texto(nodo)
        partes, cursor = [], nodo.start_byte
        for hijo in nodo.children:
            partes.append(self.fuente[cursor:hijo.start_byte].decode("utf-8", errors="replace"))
            partes.append(reemplazos[hijo.id] if reemplazos and hijo.id in reemplazos else self.reescribir(hijo))
            cursor = hijo.end_byte
        partes.append(self.fuente[cursor:nodo.end_byte].decode("utf-8", errors="replace"))
        return "".join(partes)

    # Construcciones -------------------------------------------------------------------------------
    def _sumando(self, indice, texto: str) -> str:
        """El índice como sumando de `a + i`: entre paréntesis si su operador tiene menos precedencia."""
        aditivo = (indice.type == "binary_expression"
                   and self.texto(indice.child_by_field_name("operator")) in ("+", "-", "*", "/", "%"))
        return texto if indice.type in _ATOMICAS or aditivo else f"({texto})"

    def _r_subscript_expression(self, nodo) -> Optional[str]:
        arreglo, indice = nodo.child_by_field_name("argument"), nodo.child_by_field_name("index")
        if arreglo is None or indice is None:
            return None
        self._anotar("subindice", self.texto(nodo),
                     f"*({self.texto(arreglo)} + {self._sumando(indice, self.texto(indice))})")
        return f"*({self.reescribir(arreglo)} + {self._sumando(indice, self.reescribir(indice))})"

    def _r_field_expression(self, nodo) -> Optional[str]:
        operador = nodo.child_by_field_name("operator")
        if operador is None or self.texto(operador) != "->":
            return None
        puntero, campo = nodo.child_by_field_name("argument"), nodo.child_by_field_name("field")
        self._anotar("flecha", self.texto(nodo), f"(*{self.texto(puntero)}).{self.texto(campo)}")
        return f"(*{self.reescribir(puntero)}).{self.texto(campo)}"

    def _r_assignment_expression(self, nodo) -> Optional[str]:
        operador = self.texto(nodo.child_by_field_name("operator"))
        if operador == "=":
            return None
        izquierda, derecha = nodo.child_by_field_name("left"), nodo.child_by_field_name("right")
        op = operador[:-1]
        derecha_original = self._operando(derecha, self.texto(derecha))
        self._anotar("asignacion_compuesta", self.texto(nodo),
                     f"{self.texto(izquierda)} = {self.texto(izquierda)} {op} {derecha_original}")
        izq = self.reescribir(izquierda)
        return f"{izq} = {izq} {op} {self._operando(derecha, self.reescribir(derecha))}"

    def _r_update_expression(self, nodo) -> Optional[str]:
        argumento, operador = nodo.child_by_field_name("argument"), self.texto(nodo.child_by_field_name("operator"))
        padre = nodo.parent
        suelta = padre is not None and (padre.type == "expression_statement"
                                         or (padre.type == "for_statement" and padre.child_by_field_name("update") == nodo)
                                         or padre.type == "comma_expression" and padre.parent is not None
                                         and padre.parent.type in ("expression_statement", "for_statement"))
        signo = "+" if operador == "++" else "-"
        if suelta:
            original = self.texto(argumento)
            self._anotar("incremento", self.texto(nodo), f"{original} = {original} {signo} 1")
            arg = self.reescribir(argumento)
            return f"{arg} = {arg} {signo} 1"
        forma = "pre" if nodo.children[0].type == operador else "post"
        self._anotar("incremento", self.texto(nodo), self.texto(nodo),
                     ADVERTENCIA_INCREMENTO_EN_EXPRESION[forma].format(a=self.texto(argumento), op=operador))
        return None

    def _r_pointer_expression(self, nodo) -> Optional[str]:
        operador, argumento = self.texto(nodo.child_by_field_name("operator")), nodo.child_by_field_name("argument")
        if operador != "&" or argumento.type != "subscript_expression":
            return None
        arreglo, indice = argumento.child_by_field_name("argument"), argumento.child_by_field_name("index")
        self._anotar("direccion_de_elemento", self.texto(nodo),
                     f"({self.texto(arreglo)} + {self._sumando(indice, self.texto(indice))})")
        return f"({self.reescribir(arreglo)} + {self._sumando(indice, self.reescribir(indice))})"

    def _r_unary_expression(self, nodo) -> Optional[str]:
        operador, argumento = self.texto(nodo.child_by_field_name("operator")), nodo.child_by_field_name("argument")
        if operador != "!" or argumento.type not in _VALORES:
            return None
        # Entre paréntesis propios (if (!p)) no hacen falta otros.
        suelto = nodo.parent is not None and nodo.parent.type == "parenthesized_expression"
        formato = "{} == 0" if suelto else "({} == 0)"
        self._anotar("negacion", self.texto(nodo), formato.format(self.texto(argumento)))
        return formato.format(self.reescribir(argumento))

    def condicion(self, nodo) -> str:
        """Una condición: un valor suelto (o un operando de && y ||) es una comparación implícita con 0."""
        if nodo.type == "parenthesized_expression":
            internos = [c for c in nodo.children if c.type not in ("(", ")")]
            if len(internos) == 1:
                return f"({self.condicion(internos[0])})"
        if nodo.type == "binary_expression" and self.texto(nodo.child_by_field_name("operator")) in ("&&", "||"):
            izquierda, derecha = nodo.child_by_field_name("left"), nodo.child_by_field_name("right")
            return self._generico(nodo, {izquierda.id: self.condicion(izquierda),
                                         derecha.id: self.condicion(derecha)})
        if nodo.type in _VALORES and not (nodo.type == "pointer_expression"
                                          and self.texto(nodo.child_by_field_name("operator")) == "&"):
            self._anotar("condicion_implicita", self.texto(nodo), f"{self.texto(nodo)} != 0")
            return f"{self.reescribir(nodo)} != 0"
        return self.reescribir(nodo)

    def _r_init_declarator(self, nodo) -> Optional[str]:
        declarador, valor = nodo.child_by_field_name("declarator"), nodo.child_by_field_name("value")
        if declarador is None or valor is None or declarador.type != "array_declarator" or valor.type != "string_literal":
            return None
        caracteres: List[str] = []
        for hijo in valor.children:
            if hijo.type == "string_content":
                caracteres.extend("'\\''" if c == "'" else f"'{c}'" for c in self.texto(hijo))
            elif hijo.type == "escape_sequence":
                caracteres.append(f"'{self.texto(hijo)}'")
        caracteres.append("'\\0'")
        if len(caracteres) > 25:
            return None  # una cadena larga no se aclara letra por letra
        equivalente = f"{self.texto(declarador)} = {{{', '.join(caracteres)}}}"
        self._anotar("cadena", self.texto(nodo), equivalente)
        return equivalente

    def _r_parameter_declaration(self, nodo) -> Optional[str]:
        declarador = nodo.child_by_field_name("declarator")
        if declarador is None:
            return None
        # El arreglo pegado al nombre (la primera dimensión) es el que pasa a ser puntero.
        interno = declarador
        while interno is not None and not (interno.type == "array_declarator"
                                           and interno.child_by_field_name("declarator").type == "identifier"):
            interno = interno.child_by_field_name("declarator")
        if interno is None:
            return None
        nombre = self.texto(interno.child_by_field_name("declarator"))
        tope, dimensiones = interno, []
        while tope.parent is not None and tope.parent.type == "array_declarator" and tope.parent != nodo:
            tamano = tope.parent.child_by_field_name("size")
            dimensiones.append(f"[{self.texto(tamano) if tamano is not None else ''}]")
            tope = tope.parent
        nuevo = f"(*{nombre}){''.join(dimensiones)}" if dimensiones else f"*{nombre}"
        inicio, fin = tope.start_byte - nodo.start_byte, tope.end_byte - nodo.start_byte
        original = self.texto(nodo)
        crudo = self.fuente[nodo.start_byte:nodo.end_byte].decode("utf-8", errors="replace")
        equivalente = crudo[:inicio] + nuevo + crudo[fin:]
        self._anotar("parametro_arreglo", original, equivalente)
        return equivalente

    def _r_expression_statement(self, nodo) -> Optional[str]:
        expresion = nodo.children[0] if nodo.children else None
        if (expresion is not None and expresion.type == "assignment_expression"
                and self.texto(expresion.child_by_field_name("operator")) == "="
                and expresion.child_by_field_name("right").type == "conditional_expression"):
            destino = self.reescribir(expresion.child_by_field_name("left"))
            return self._ternario(expresion.child_by_field_name("right"), lambda v: f"{destino} = {v};",
                                  self.texto(nodo))
        return None

    def _r_return_statement(self, nodo) -> Optional[str]:
        valores = [c for c in nodo.children if c.type not in ("return", ";")]
        if len(valores) == 1 and valores[0].type == "conditional_expression":
            return self._ternario(valores[0], lambda v: f"return {v};", self.texto(nodo))
        return None

    def _ternario(self, nodo, sentencia, original: str) -> str:
        condicion = nodo.child_by_field_name("condition")
        si, no = nodo.child_by_field_name("consequence"), nodo.child_by_field_name("alternative")
        equivalente_original = (f"if ({self.texto(condicion)}) {sentencia(self.texto(si))} "
                                f"else {sentencia(self.texto(no))}")
        self._anotar("ternario", original, equivalente_original)
        return (f"if ({self.condicion(condicion)}) {sentencia(self.reescribir(si))} "
                f"else {sentencia(self.reescribir(no))}")

    # Unidades: lo que se muestra como «sentencia original ≡ sentencia equivalente» -----------------
    def unidad(self, nodo, reescrito=None, original: Optional[str] = None) -> None:
        antes = len(self._equivalencias)
        texto = reescrito() if reescrito else self.reescribir(nodo)
        nuevas = self._equivalencias[antes:]
        if nuevas:
            self.sentencias.append(Sentencia(nodo.start_point[0] + 1, original or self.texto(nodo), texto, nuevas))

    def _for(self, nodo) -> None:
        inicial = nodo.child_by_field_name("initializer")
        condicion = nodo.child_by_field_name("condition")
        actualizacion = nodo.child_by_field_name("update")
        cuerpo = nodo.child_by_field_name("body")
        crudo = self.fuente[nodo.start_byte:(cuerpo.start_byte if cuerpo else nodo.end_byte)]
        cabecera = crudo.decode("utf-8", errors="replace").strip()

        def reescrito() -> str:
            lineas = []
            if inicial is not None:
                ini = self.reescribir(inicial)
                lineas.append(ini if ini.rstrip().endswith(";") else f"{ini};")
            cond = self.condicion(condicion) if condicion is not None else "1"
            interior = ["    …cuerpo…"]
            if actualizacion is not None:
                interior.append(f"    {self.reescribir(actualizacion)};")
            bucle = [f"while ({cond}) {{", *interior, "}"]
            if lineas:
                return "\n".join(["{", *("    " + l for l in lineas), *("    " + l for l in bucle), "}"])
            return "\n".join(bucle)

        advertencia = ADVERTENCIA_CONTINUE if cuerpo is not None and _tiene_continue(cuerpo) else ""
        antes = len(self._equivalencias)
        self._anotar("for", cabecera, "{ ini; while (cond) { cuerpo inc; } }", advertencia)
        texto = reescrito()
        self.sentencias.append(Sentencia(nodo.start_point[0] + 1, cabecera, texto, self._equivalencias[antes:]))

    def recorrer(self, nodo) -> None:
        tipo = nodo.type
        if tipo in ("expression_statement", "declaration", "return_statement", "field_declaration"):
            self.unidad(nodo)
            return
        if tipo == "function_definition":
            declarador = nodo.child_by_field_name("declarator")
            if declarador is not None:
                # La firma completa: tipo de retorno y nombre, no solo el declarador.
                tipo_retorno = self.fuente[nodo.start_byte:declarador.start_byte].decode("utf-8", errors="replace")
                self.unidad(declarador, lambda: tipo_retorno + self.reescribir(declarador),
                            original=tipo_retorno + self.texto(declarador))
            cuerpo = nodo.child_by_field_name("body")
            if cuerpo is not None:
                self.recorrer(cuerpo)
            return
        if tipo == "for_statement":
            self._for(nodo)
            cuerpo = nodo.child_by_field_name("body")
            if cuerpo is not None:
                self.recorrer(cuerpo)
            return
        if tipo in ("if_statement", "while_statement", "do_statement", "switch_statement"):
            condicion = nodo.child_by_field_name("condition")
            for hijo in nodo.children:
                if hijo == condicion:
                    palabra = tipo.split("_")[0]
                    self.unidad(hijo, lambda h=hijo, palabra=palabra: f"{palabra} {self.condicion(h) if palabra != 'switch' else self.reescribir(h)}",
                                original=f"{palabra} {self.texto(hijo)}")
                else:
                    self.recorrer(hijo)
            return
        for hijo in nodo.children:
            self.recorrer(hijo)


def _tiene_continue(nodo) -> bool:
    """Un continue de este bucle (no de un bucle anidado)."""
    for hijo in nodo.children:
        if hijo.type == "continue_statement":
            return True
        if hijo.type not in _BUCLES and _tiene_continue(hijo):
            return True
    return False


def _tiene_errores(nodo) -> bool:
    return bool(nodo.has_error)


ENVOLTORIO = "void gaff_fragmento(void)\n{\n"


def explicar(codigo: str, linea: Optional[int] = None) -> List[Sentencia]:
    """Las sentencias de `codigo` que usan azúcar sintáctico, con su equivalente.

    Un fragmento suelto (sentencias fuera de una función) se analiza dentro de una función.
    """
    parser = _parser()
    fuente = codigo.encode("utf-8")
    arbol = parser.parse(fuente)
    desplazamiento = 0
    if _tiene_errores(arbol.root_node):
        envuelto = (ENVOLTORIO + codigo + "\n}\n").encode("utf-8")
        arbol_envuelto = parser.parse(envuelto)
        if not _tiene_errores(arbol_envuelto.root_node):
            fuente, arbol, desplazamiento = envuelto, arbol_envuelto, ENVOLTORIO.count("\n")
    desazucarador = _Desazucarador(fuente)
    desazucarador.recorrer(arbol.root_node)
    sentencias = []
    for s in desazucarador.sentencias:
        if "gaff_fragmento" in s.original:
            continue
        s.linea -= desplazamiento
        if linea is None or s.linea <= linea <= s.linea + s.original.count("\n"):
            sentencias.append(s)
    return sentencias


def tipos_usados(sentencias: List[Sentencia]) -> List[str]:
    vistos: List[str] = []
    for s in sentencias:
        for e in s.equivalencias:
            if e.tipo not in vistos:
                vistos.append(e.tipo)
    return vistos
