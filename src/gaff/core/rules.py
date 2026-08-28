"""Catálogo y definiciones de reglas de estilo de cátedra en GAFF, alineado con p1-apunte/reglas."""

from __future__ import annotations

from typing import Any, Dict

CATALOGO_REGLAS: Dict[str, Dict[str, Any]] = {
    "0x0007h": {
        "codigo": "0x0007h",
        "alias": "GAFF001",
        "titulo": "Los argumentos y variables locales deben usar snake_case en minúsculas",
        "descripcion": "Todos los identificadores de variables y argumentos deben estar escritos en minúsculas separadas por guiones bajos (snake_case), evitando camelCase o PascalCase.",
        "ejemplo_correcto": "int calcular_promedio(int *vector, size_t longitud);",
        "ejemplo_incorrecto": "int calcularPromedio(int *Vector, size_t Longitud);",
        "autofix": "No",
    },
    "0x3004h": {
        "codigo": "0x3004h",
        "alias": "GAFF002",
        "titulo": "Utilizá typedef para definir tipos de estructuras con el sufijo _t",
        "descripcion": "Los tipos creados mediante typedef (structs, enums, unions) deben identificarse con sufijo '_t' (o prefijo 't_').",
        "ejemplo_correcto": "typedef struct nodo nodo_t;\ntypedef enum estado estado_t;",
        "ejemplo_incorrecto": "typedef struct nodo Nodo;",
        "autofix": "No",
    },
    "0x2004h": {
        "codigo": "0x2004h",
        "alias": "GAFF003",
        "titulo": "No se permite el uso de variables globales",
        "descripcion": "No se permite el uso de variables globales mutables fuera del alcance de las funciones. Toda comunicación de estado debe realizarse vía parámetros y retornos.",
        "ejemplo_correcto": "const double PI = 3.14159265;\n#define BUFFER_MAX 1024",
        "ejemplo_incorrecto": "int contador_global = 0;",
        "autofix": "No",
    },
    "0x2005h": {
        "codigo": "0x2005h",
        "alias": "GAFF004",
        "titulo": "Cada función debe tener una única responsabilidad (<= 50 líneas)",
        "descripcion": "Las funciones no deben exceder las 50 líneas de código para garantizar modularidad, legibilidad y responsabilidad única.",
        "ejemplo_correcto": "Dividir funciones complejas en funciones auxiliares privadas (static).",
        "ejemplo_incorrecto": "Una función main() o procesar() de 150 líneas continuas.",
        "autofix": "No",
    },
    "0x5003h": {
        "codigo": "0x5003h",
        "alias": "GAFF005",
        "titulo": "Utilizá guardas de inclusión en todos los archivos de cabecera",
        "descripcion": "Todo archivo de cabecera (.h) debe incluir guardas de preprocesador (#ifndef ARCHIVO_H / #define ARCHIVO_H / #endif) o #pragma once.",
        "ejemplo_correcto": "#ifndef LISTA_H\n#define LISTA_H\n...\n#endif /* LISTA_H */",
        "ejemplo_incorrecto": "Archivo lista.h sin guardas de inclusión.",
        "autofix": "Sí",
    },
    "0x300Dh": {
        "codigo": "0x300Dh",
        "alias": "GAFF006",
        "titulo": "Utilizá enum o constantes en lugar de números mágicos",
        "descripcion": "No utilizar literales numéricos sin contexto en el cuerpo del código (distintos de 0, 1, 2, -1). Definir constantes con #define o enum.",
        "ejemplo_correcto": "#define MAX_INTENTOS 5\nfor (int i = 0; i < MAX_INTENTOS; i++)",
        "ejemplo_incorrecto": "for (int i = 0; i < 5; i++) // ¿Qué significa 5?",
        "autofix": "No",
    },
    "0x0004h": {
        "codigo": "0x0004h",
        "alias": "GAFF007",
        "titulo": "Un espacio antes y después de cada operador binario y palabra clave",
        "descripcion": "Debe dejarse un espacio en blanco entre la palabra clave de control y el paréntesis de apertura ('if (', 'for (', 'while (', 'switch (') y alrededor de operadores.",
        "ejemplo_correcto": "if (x > 0) { ... }",
        "ejemplo_incorrecto": "if(x > 0){ ... }",
        "autofix": "Sí",
    },
    "0x1006h": {
        "codigo": "0x1006h",
        "alias": "GAFF008",
        "titulo": "No utilizar la instrucción goto",
        "descripcion": "El uso de 'goto' está estrictamente prohibido en el paradigma de programación estructurada de la cátedra.",
        "ejemplo_correcto": "Utilizar estructuras de bucle y retorno limpio anticipado.",
        "ejemplo_incorrecto": "goto cleanup;",
        "autofix": "No",
    },
    "0x0009h": {
        "codigo": "0x0009h",
        "alias": "GAFF009",
        "titulo": "Las líneas de código no deben exceder los 79 caracteres",
        "descripcion": "Las líneas de código no deben superar los 79-80 caracteres de ancho para evitar scroll horizontal en editores.",
        "ejemplo_correcto": "Partir llamadas con muchos parámetros en varias líneas identadas.",
        "ejemplo_incorrecto": "Una línea de 140 caracteres con asignaciones y llamadas anidadas.",
        "autofix": "No",
    },
    "0x0005h": {
        "codigo": "0x0005h",
        "alias": "GAFF010",
        "titulo": "Cada bloque debe tener una indentación de cuatro espacios (sin tabs)",
        "descripcion": "Las líneas no deben contener espacios en blanco sobrantes al final ni mezclar tabuladores duros con espacios. La indentación debe ser exactamente de 4 espacios.",
        "ejemplo_correcto": "Indentación consistente de 4 espacios sin espacios al final de línea.",
        "ejemplo_incorrecto": "Líneas con espacios invisibles al final o tabuladores de 8 columnas.",
        "autofix": "Sí",
    },
}

# Alias bidireccionales para retrocompatibilidad
ALIAS_MAP: Dict[str, str] = {
    "GAFF001": "0x0007h",
    "GAFF002": "0x3004h",
    "GAFF003": "0x2004h",
    "GAFF004": "0x2005h",
    "GAFF005": "0x5003h",
    "GAFF006": "0x300Dh",
    "GAFF007": "0x0004h",
    "GAFF008": "0x1006h",
    "GAFF009": "0x0009h",
    "GAFF010": "0x0005h",
}

for k, v in ALIAS_MAP.items():
    if v in CATALOGO_REGLAS:
        CATALOGO_REGLAS[k] = CATALOGO_REGLAS[v]
