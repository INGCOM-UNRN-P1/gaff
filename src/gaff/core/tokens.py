"""Los tokens del fuente según tree-sitter, para las reglas que miden espacios.

Una regla sobre líneas de texto no sabe qué es cada carácter: hay que tapar literales y comentarios,
y aun así un `*` puede ser multiplicación, desreferencia o parte de un declarador, y `1e-5` parece una
resta. Acá cada token trae su tipo y el de su padre en el árbol, y literales y comentarios son un
token entero, así que su contenido no se mira por construcción.

Quedan afuera los comentarios y las líneas del preprocesador, que tienen otras reglas.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterator, List, Optional, Sequence, Tuple

import tree_sitter_c as tsc
from tree_sitter import Language, Node, Parser

# No se entra a estos nodos: son un token para las reglas de espacios.
ATOMICOS = ("string_literal", "char_literal", "system_lib_string", "preproc_arg", "comment", "number_literal")

_PARSER: Optional[Parser] = None


def _parser() -> Parser:
    global _PARSER
    if _PARSER is None:
        _PARSER = Parser(Language(tsc.language()))
    return _PARSER


@dataclass(frozen=True)
class Token:
    tipo: str
    texto: str
    padre: str  # el tipo del nodo que lo contiene
    fila: int  # desde 0
    columna: int  # en caracteres, desde 0
    fin: int

    @property
    def es_palabra(self) -> bool:
        """Identificador, número o palabra clave: lo que una regla de operadores tiene a los lados."""
        return self.texto[:1].isalnum() or self.texto[:1] == "_"


def _hojas(raiz: Node) -> Iterator[Node]:
    """Con una pila propia: un programa muy anidado agotaría la del intérprete."""
    pendientes = [raiz]
    while pendientes:
        nodo = pendientes.pop()
        if nodo.type in ATOMICOS or nodo.child_count == 0:
            yield nodo
        else:
            pendientes.extend(reversed(nodo.children))


def tokens_de(contenido: str, lineas_de_codigo: Sequence[str]) -> List[Token]:
    """Los tokens de `contenido`. `lineas_de_codigo` son sus líneas sin comentarios: dicen cuáles son
    del preprocesador."""
    fuente = contenido.encode("utf-8", errors="replace")
    filas = fuente.split(b"\n")

    def caracteres(fila: int, bytes_: int) -> int:
        return len(filas[fila][:bytes_].decode("utf-8", errors="replace"))

    tokens: List[Token] = []
    for hoja in _hojas(_parser().parse(fuente).root_node):
        fila = hoja.start_point.row
        if hoja.type == "comment" or hoja.start_byte == hoja.end_byte:
            continue
        if fila < len(lineas_de_codigo) and lineas_de_codigo[fila].lstrip().startswith("#"):
            continue
        columna = caracteres(fila, hoja.start_point.column)
        multilinea = hoja.end_point.row != fila
        texto = (hoja.text or b"").decode("utf-8", errors="replace")
        fin = columna + len(texto) if not multilinea else columna + 1
        tokens.append(Token(hoja.type, texto, hoja.parent.type if hoja.parent else "", fila, columna, fin))
    return tokens


def por_fila(tokens: Sequence[Token]) -> Dict[int, List[Token]]:
    filas: Dict[int, List[Token]] = {}
    for token in tokens:
        filas.setdefault(token.fila, []).append(token)
    return filas


def contiguos(tokens: Sequence[Token]) -> Iterator[Tuple[Token, Token]]:
    """Los pares de tokens seguidos en una misma línea."""
    for anterior, siguiente in zip(tokens, tokens[1:], strict=False):
        if anterior.fila == siguiente.fila:
            yield anterior, siguiente


def separacion(anterior: Token, siguiente: Token) -> int:
    return siguiente.columna - anterior.fin
