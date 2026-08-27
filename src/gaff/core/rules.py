"""Catálogo y definiciones de reglas de estilo de cátedra en GAFF."""

from __future__ import annotations

from typing import Dict

CATALOGO_REGLAS: Dict[str, Dict[str, str]] = {
    "GAFF001": {
        "titulo": "Nombres de funciones y variables en snake_case",
        "descripcion": "Todos los identificadores de variables y funciones deben estar escritos en minúsculas separadas por guiones bajos (snake_case), evitando camelCase o PascalCase.",
        "ejemplo_correcto": "int calcular_promedio(int* vector, size_t longitud);",
        "ejemplo_incorrecto": "int calcularPromedio(int* Vector, size_t Longitud);",
        "autofix": "No",
    },
    "GAFF002": {
        "titulo": "Nomenclatura de tipos definidos (t_ o _t)",
        "descripcion": "Los tipos creados mediante typedef (structs, enums, unions) deben identificarse con prefijo 't_' o sufijo '_t'.",
        "ejemplo_correcto": "typedef struct nodo t_nodo;\ntypedef enum estado estado_t;",
        "ejemplo_incorrecto": "typedef struct nodo Nodo;",
        "autofix": "No",
    },
    "GAFF003": {
        "titulo": "Prohibición de variables globales mutables",
        "descripcion": "No se permite el uso de variables globales mutables fuera del alcance de las funciones. Toda comunicación de estado debe realizarse vía parámetros y retornos.",
        "ejemplo_correcto": "const double PI = 3.14159265;\n#define BUFFER_MAX 1024",
        "ejemplo_incorrecto": "int contador_global = 0;",
        "autofix": "No",
    },
    "GAFF004": {
        "titulo": "Longitud máxima de función (<= 50 líneas)",
        "descripcion": "Las funciones no deben exceder las 50 líneas de código para garantizar modularidad, legibilidad y responsabilidad única.",
        "ejemplo_correcto": "Dividir funciones complejas en funciones auxiliares privadas (static).",
        "ejemplo_incorrecto": "Una función main() o procesar() de 150 líneas continuas.",
        "autofix": "No",
    },
    "GAFF005": {
        "titulo": "Guardas de inclusión obligatorias en cabeceras (.h)",
        "descripcion": "Todo archivo de cabecera (.h) debe incluir guardas de preprocesador (#ifndef ARCHIVO_H / #define ARCHIVO_H / #endif) o #pragma once.",
        "ejemplo_correcto": "#ifndef LISTA_H\n#define LISTA_H\n...\n#endif // LISTA_H",
        "ejemplo_incorrecto": "Archivo lista.h sin guardas de inclusión.",
        "autofix": "Sí",
    },
    "GAFF006": {
        "titulo": "Prohibición de números mágicos (Magic Numbers)",
        "descripcion": "No utilizar literales numéricos sin contexto en el cuerpo del código (distintos de 0, 1, 2, -1). Definir constantes con #define o enum.",
        "ejemplo_correcto": "#define MAX_INTENTOS 5\nfor (int i = 0; i < MAX_INTENTOS; i++)",
        "ejemplo_incorrecto": "for (int i = 0; i < 5; i++) // ¿Qué significa 5?",
        "autofix": "No",
    },
    "GAFF007": {
        "titulo": "Espaciado de palabras clave de control (if, for, while, switch)",
        "descripcion": "Debe dejarse un espacio en blanco entre la palabra clave de control y el paréntesis de apertura: 'if (', 'for (', 'while (', 'switch ('.",
        "ejemplo_correcto": "if (x > 0) { ... }",
        "ejemplo_incorrecto": "if(x > 0){ ... }",
        "autofix": "Sí",
    },
    "GAFF008": {
        "titulo": "Prohibición de la sentencia goto",
        "descripcion": "El uso de 'goto' está estrictamente prohibido en el paradigma de programación estructurada de la cátedra.",
        "ejemplo_correcto": "Utilizar estructuras de bucle y retorno limpio anticipado.",
        "ejemplo_incorrecto": "goto cleanup;",
        "autofix": "No",
    },
    "GAFF009": {
        "titulo": "Longitud máxima de línea (<= 100 caracteres)",
        "descripcion": "Las líneas de código no deben superar los 100 caracteres de ancho para evitar scroll horizontal en editores divididos.",
        "ejemplo_correcto": "Partir llamadas con muchos parámetros en varias líneas identadas.",
        "ejemplo_incorrecto": "Una línea de 140 caracteres con asignaciones y llamadas anidadas.",
        "autofix": "No",
    },
    "GAFF010": {
        "titulo": "Limpieza de espacios finales y mezcla de tabuladores",
        "descripcion": "Las líneas no deben contener espacios en blanco sobrantes al final (trailing whitespace) ni mezclar tabuladores duros con espacios.",
        "ejemplo_correcto": "Indentación consistente de 4 espacios sin espacios al final de línea.",
        "ejemplo_incorrecto": "Líneas con espacios invisibles al final o tabuladores de 8 columnas.",
        "autofix": "Sí",
    },
}
