"""Catálogo y definiciones de reglas de estilo de cátedra en GAFF, alineado con p1-apunte/reglas."""

from __future__ import annotations

import os
from pathlib import Path
import re
from typing import Any, Dict, Optional

CATALOGO_REGLAS: Dict[str, Dict[str, Any]] = {
    # 0x00XXh: Sintaxis Básica y Nomenclatura
    "0x0000h": {
        "codigo": "0x0000h",
        "titulo": "La claridad y prolijidad son de máxima importancia",
        "descripcion": "El código debe ser claro y fácil de entender para cualquier lector. Un código limpio y prolijo previene errores y facilita el mantenimiento.",
        "ejemplo_correcto": "int i = 0;\nwhile (i < limite) {\n    printf(\"%d\", i);\n    i++;\n}",
        "ejemplo_incorrecto": "for (int i=0,j=10;i<j;i++,j--) { printf(\"%d\", i+j); }",
        "autofix": "No",
    },
    "0x0001h": {
        "codigo": "0x0001h",
        "titulo": "Los identificadores deben ser descriptivos",
        "descripcion": "Los nombres de variables y argumentos deben reflejar con precisión su propósito. Evitá variables de una sola letra (salvo índices canónicos i, j, k, n, x, y, z, f, c, r).",
        "ejemplo_correcto": "int precio_total = obtener_precio();",
        "ejemplo_incorrecto": "int a = obtener_precio();",
        "autofix": "No",
    },
    "0x0002h": {
        "codigo": "0x0002h",
        "titulo": "Una declaración de variable por línea",
        "descripcion": "Declarar cada variable en una línea separada para facilitar comentarios y legibilidad.",
        "ejemplo_correcto": "int primer_valor;\nint segundo_valor;",
        "ejemplo_incorrecto": "int primer_valor, segundo_valor, tercer_valor;",
        "autofix": "No",
    },
    "0x0003h": {
        "codigo": "0x0003h",
        "titulo": "Siempre debés inicializar las variables a un valor conocido",
        "descripcion": "Inicializar las variables locales al declararlas para evitar valores residuales del stack.",
        "ejemplo_correcto": "int contador = 0;\nstruct datos_t d = {0};",
        "ejemplo_incorrecto": "int contador;\nstruct datos_t d;",
        "autofix": "No",
    },
    "0x0004h": {
        "codigo": "0x0004h",
        "titulo": "Un espacio antes y después de cada operador binario y palabra clave",
        "descripcion": "Debe dejarse un espacio en blanco entre la palabra clave de control y el paréntesis ('if (', 'for (', 'while (', 'switch (') y alrededor de operadores binarios.",
        "ejemplo_correcto": "if (x > 0) {\n    total = valor1 + valor2;\n}",
        "ejemplo_incorrecto": "if(x>0){\n    total=valor1+valor2;\n}",
        "autofix": "Sí",
    },
    "0x0005h": {
        "codigo": "0x0005h",
        "titulo": "Cada bloque debe tener una indentación de cuatro espacios (sin tabs ni trailing)",
        "descripcion": "La indentación debe ser exactamente de 4 espacios respecto al contenedor. No se permiten tabuladores duros (\\t) ni espacios sobrantes al final de línea.",
        "ejemplo_correcto": "void funcion(void)\n{\n    int x = 10;\n}",
        "ejemplo_incorrecto": "void funcion(void){\n\tint x = 10;   \n}",
        "autofix": "Sí",
    },
    "0x0006h": {
        "codigo": "0x0006h",
        "titulo": "El asterisco de los punteros debe declararse junto al identificador",
        "descripcion": "Declarar el asterisco junto al nombre de la variable ('int *ptr') y no junto al tipo ('int* ptr').",
        "ejemplo_correcto": "int *ptr;\nchar *nombre;",
        "ejemplo_incorrecto": "int* ptr;\nchar* nombre;",
        "autofix": "Sí",
    },
    "0x0007h": {
        "codigo": "0x0007h",
        "titulo": "Los argumentos y variables locales deben usar snake_case en minúsculas",
        "descripcion": "Todos los identificadores de variables y argumentos deben estar escritos en snake_case en minúsculas, evitando camelCase o PascalCase.",
        "ejemplo_correcto": "int calcular_promedio(int *vector_numeros, size_t longitud_total);",
        "ejemplo_incorrecto": "int calcularPromedio(int *vectorNumeros, size_t LongitudTotal);",
        "autofix": "No",
    },
    "0x0008h": {
        "codigo": "0x0008h",
        "titulo": "Las constantes deben nombrarse en MAYUSCULAS_SNAKE_CASE",
        "descripcion": "Las constantes (#define y const) deben escribirse enteramente en MAYUSCULAS_SNAKE_CASE.",
        "ejemplo_correcto": "#define BUFFER_MAX 1024\nconst int DIAS_SEMANA = 7;",
        "ejemplo_incorrecto": "#define buffer_max 1024\nconst int diasSemana = 7;",
        "autofix": "No",
    },
    "0x0009h": {
        "codigo": "0x0009h",
        "titulo": "Las líneas de código no deben exceder los 79-80 caracteres",
        "descripcion": "Las líneas de código no deben superar los 80 caracteres de ancho para evitar desplazamiento horizontal.",
        "ejemplo_correcto": "printf(\"Mensaje largo dividido \"\n       \"en dos líneas continuas.\\n\");",
        "ejemplo_incorrecto": "printf(\"Este es un mensaje de texto extremadamente largo que supera los ochenta caracteres en una sola línea.\\n\");",
        "autofix": "No",
    },
    "0x000Ah": {
        "codigo": "0x000Ah",
        "titulo": "Escribí comentarios que expliquen el 'porqué', no el 'qué'",
        "descripcion": "Los comentarios deben aportar valor justificando decisiones de diseño y no repetir lo evidente ni estar vacíos.",
        "ejemplo_correcto": "// Usamos índice inverso porque el último byte define la paridad del paquete\nfor (size_t i = len - 1; i < len; i--)",
        "ejemplo_incorrecto": "// Incrementa i en 1\ni++;",
        "autofix": "No",
    },
    "0x000Bh": {
        "codigo": "0x000Bh",
        "titulo": "Las llaves deben ubicarse en líneas independientes según el estilo Allman",
        "descripcion": "Ubicar las llaves de apertura y cierre en líneas separadas alineadas con la instrucción de control.",
        "ejemplo_correcto": "if (x > 0)\n{\n    return x;\n}",
        "ejemplo_incorrecto": "if (x > 0) {\n    return x;\n}",
        "autofix": "Sí",
    },

    # 0x10XXh: Estructuras de Control y Lazos
        "0x000Ch": {
        "codigo": "0x000Ch",
        "titulo": "Los nombres de los archivos deben usar snake_case en minúsculas (sin espacios)",
        "descripcion": "Los nombres de archivos fuentes y cabeceras deben escribirse exclusivamente en snake_case en minúsculas, sin espacios ni caracteres especiales.",
        "ejemplo_correcto": "lista_enlazada.c\narbol_binario.h",
        "ejemplo_incorrecto": "Lista Enlazada.c\nArbolBinario.H\nmi-archivo.c",
        "autofix": "No",
    },
    "0x1001h": {
        "codigo": "0x1001h",
        "titulo": "Todas las estructuras de control deben utilizar llaves",
        "descripcion": "Las sentencias if, else, for, while deben incluir siempre llaves {}, incluso para bloques de una sola línea.",
        "ejemplo_correcto": "if (x > 0)\n{\n    x++;\n}",
        "ejemplo_incorrecto": "if (x > 0)\n    x++;",
        "autofix": "No",
    },
    "0x1002h": {
        "codigo": "0x1002h",
        "titulo": "Evitá continue y break descontrolado; preferí banderas lógicas",
        "descripcion": "El uso de continue está estrictamente prohibido y break debe reservarse para simplificaciones claras o dentro de switch.",
        "ejemplo_correcto": "bool seguir = true;\nwhile (i < 10 && seguir) { ... }",
        "ejemplo_incorrecto": "for (int i = 0; i < 10; i++) { if (i == 4) continue; }",
        "autofix": "No",
    },
    "0x1003h": {
        "codigo": "0x1003h",
        "titulo": "Utilizá for para conteo definido y while para lazos lógicos",
        "descripcion": "No forzar lecturas interactivas o lazos indefinidos (for(;;)) dentro del encabezado for.",
        "ejemplo_correcto": "while (numero != 0) { scanf(\"%d\", &numero); }",
        "ejemplo_incorrecto": "for (scanf(\"%d\", &n); n != 0; scanf(\"%d\", &n)) { ... }",
        "autofix": "No",
    },
    "0x1004h": {
        "codigo": "0x1004h",
        "titulo": "Las condiciones complejas deben ser simplificadas o comentadas",
        "descripcion": "Dividir expresiones booleanas complejas con múltiples operadores usando variables intermedias explicativas.",
        "ejemplo_correcto": "bool es_valido = usuario_activo && tiene_permisos;\nif (es_valido) { ... }",
        "ejemplo_incorrecto": "if ((usuario_activo && tiene_permisos && !mantenimiento) || (es_admin && clave_maestra))",
        "autofix": "No",
    },
    "0x1005h": {
        "codigo": "0x1005h",
        "titulo": "Evitá condiciones ambiguas basadas en truthiness",
        "descripcion": "Comparar explícitamente contra NULL, contra '\\0' o contra 0 en lugar de confiar en conversiones booleanas implícitas.",
        "ejemplo_correcto": "if (ptr != NULL)\nif (caracter == '\\0')",
        "ejemplo_incorrecto": "if (ptr)\nif (!caracter)",
        "autofix": "No",
    },
    "0x1006h": {
        "codigo": "0x1006h",
        "titulo": "No utilizar la instrucción goto",
        "descripcion": "El uso de 'goto' está estrictamente prohibido en el paradigma de programación estructurada de la cátedra.",
        "ejemplo_correcto": "Utilizar estructuras de bucle y retornos limpios estructurados.",
        "ejemplo_incorrecto": "goto cleanup;",
        "autofix": "No",
    },
    "0x1007h": {
        "codigo": "0x1007h",
        "titulo": "No utilizar el operador condicional (ternario) ?:",
        "descripcion": "El operador ternario complica la lectura; utilizá if-else estructurado.",
        "ejemplo_correcto": "if (a > b) {\n    res = a;\n} else {\n    res = b;\n}",
        "ejemplo_incorrecto": "res = (a > b) ? a : b;",
        "autofix": "No",
    },
    "0x1008h": {
        "codigo": "0x1008h",
        "titulo": "Toda instrucción switch debe incluir un caso default",
        "descripcion": "Incluir siempre default: al final de un bloque switch para manejar estados no previstos.",
        "ejemplo_correcto": "switch (cmd) {\n    case 1: ... break;\n    default: ... break;\n}",
        "ejemplo_incorrecto": "switch (cmd) {\n    case 1: ... break;\n}",
        "autofix": "No",
    },

    # 0x20XXh: Funciones y Modularización
    "0x2001h": {
        "codigo": "0x2001h",
        "titulo": "Usar cláusulas de guarda para evitar anidación profunda",
        "descripcion": "Validar precondiciones y salir tempranamente para evitar código en flecha (anidación > 3 niveles).",
        "ejemplo_correcto": "if (s == NULL) return -1;\nif (s->activo == false) return -1;",
        "ejemplo_incorrecto": "if (s != NULL) { if (s->activo) { if (s->val > 0) { ... } } }",
        "autofix": "No",
    },
    "0x2002h": {
        "codigo": "0x2002h",
        "titulo": "Las funciones auxiliares no deben contener printf o scanf",
        "descripcion": "Separar la lógica computacional del código de entrada/salida por consola.",
        "ejemplo_correcto": "float calcular_iva(float monto) { return monto * 0.21f; }",
        "ejemplo_incorrecto": "void calcular_iva(float monto) { printf(\"IVA: %f\\n\", monto * 0.21f); }",
        "autofix": "No",
    },
    "0x2003h": {
        "codigo": "0x2003h",
        "titulo": "Todas las funciones deben incluir documentación completa",
        "descripcion": "Documentar funciones con @brief, @param y @return en formato Doxygen.",
        "ejemplo_correcto": "/**\n * @brief Suma dos enteros.\n * @param a Primer sumando.\n * @param b Segundo sumando.\n * @return Resultado de la suma.\n */",
        "ejemplo_incorrecto": "int suma(int a, int b);",
        "autofix": "Sí",
    },
    "0x2004h": {
        "codigo": "0x2004h",
        "titulo": "No se permite el uso de variables globales mutables",
        "descripcion": "No se permite el uso de variables globales mutables fuera del alcance de las funciones. Toda comunicación debe ser vía parámetros y retornos.",
        "ejemplo_correcto": "const double PI = 3.14159265;\n#define BUFFER_MAX 1024",
        "ejemplo_incorrecto": "int contador_global = 0;",
        "autofix": "No",
    },
    "0x2005h": {
        "codigo": "0x2005h",
        "titulo": "Cada función debe tener una única responsabilidad (<= 50 líneas)",
        "descripcion": "Las funciones no deben exceder las 50 líneas de código para garantizar modularidad, legibilidad y responsabilidad única.",
        "ejemplo_correcto": "Dividir funciones complejas en funciones auxiliares privadas (static).",
        "ejemplo_incorrecto": "Una función procesar_todo() de 120 líneas continuas.",
        "autofix": "No",
    },
    "0x2006h": {
        "codigo": "0x2006h",
        "titulo": "Una aserción por cada función de prueba",
        "descripcion": "Modularizar las pruebas unitarias enfocando cada test en un caso atómico.",
        "ejemplo_correcto": "void test_suma_positivos() { assert(sumar(2, 2) == 4); }",
        "ejemplo_incorrecto": "void test_todo() { assert(sumar(2,2)==4); assert(restar(4,2)==2); assert(mult(2,3)==6); }",
        "autofix": "No",
    },
    "0x2007h": {
        "codigo": "0x2007h",
        "titulo": "Mantené el alcance de las variables al mínimo posible",
        "descripcion": "Declarar las variables en el bloque más interno donde sean utilizadas.",
        "ejemplo_correcto": "for (int i = 0; i < n; i++) { ... }",
        "ejemplo_incorrecto": "int i; // 100 líneas arriba del for\n...",
        "autofix": "No",
    },
    "0x2008h": {
        "codigo": "0x2008h",
        "titulo": "Los valores de retorno deben definirse como constantes o enum",
        "descripcion": "Reemplazar códigos de retorno numéricos mágicos por constantes descriptivas o enum.",
        "ejemplo_correcto": "return ESTADO_OK;\nreturn ERROR_PARAMETRO_INVALIDO;",
        "ejemplo_incorrecto": "return 1;\nreturn -1;",
        "autofix": "No",
    },
    "0x2009h": {
        "codigo": "0x2009h",
        "titulo": "Los ejercicios deben ser resueltos mediante funciones",
        "descripcion": "No colocar toda la lógica del problema dentro de la función main(). Modularizar en funciones.",
        "ejemplo_correcto": "int main(void) { procesar_datos(); return 0; }",
        "ejemplo_incorrecto": "int main(void) { // 80 líneas con toda la lógica del ejercicio\n}",
        "autofix": "No",
    },
    "0x200Ah": {
        "codigo": "0x200Ah",
        "titulo": "Nombres de funciones deben usar snake_case en minúsculas",
        "descripcion": "Los identificadores de función deben estar en snake_case.",
        "ejemplo_correcto": "int calcular_total(int base, int impuesto);",
        "ejemplo_incorrecto": "int CalcularTotal(int Base, int Impuesto);",
        "autofix": "No",
    },

    # 0x30XXh: Punteros y Gestión de Memoria
    "0x3001h": {
        "codigo": "0x3001h",
        "titulo": "Siempre verificá la asignación exitosa de memoria dinámica",
        "descripcion": "Comprobar siempre if (ptr == NULL) tras llamar a malloc, calloc o realloc.",
        "ejemplo_correcto": "ptr = malloc(sizeof(*ptr));\nif (ptr == NULL) {\n    return NULL;\n}",
        "ejemplo_incorrecto": "ptr = malloc(sizeof(*ptr));\nptr->dato = 10; // Falla si no hay memoria",
        "autofix": "No",
    },
    "0x3002h": {
        "codigo": "0x3002h",
        "titulo": "Asigná NULL al puntero tras free() para evitar punteros colgantes",
        "descripcion": "Hacer ptr = NULL inmediatamente tras free(ptr); para evitar dangling pointers.",
        "ejemplo_correcto": "free(ptr);\nptr = NULL;",
        "ejemplo_incorrecto": "free(ptr);\n// ptr sigue apuntando a memoria liberada",
        "autofix": "No",
    },
    "0x3003h": {
        "codigo": "0x3003h",
        "titulo": "No mezcles asignación y comparación en una sola línea",
        "descripcion": "Separar la asignación de memoria de la comparación contra NULL.",
        "ejemplo_correcto": "ptr = malloc(tamano);\nif (ptr == NULL) { ... }",
        "ejemplo_incorrecto": "if ((ptr = malloc(tamano)) == NULL) { ... }",
        "autofix": "No",
    },
    "0x3004h": {
        "codigo": "0x3004h",
        "titulo": "Utilizá typedef para definir tipos de estructuras con el sufijo _t",
        "descripcion": "Los tipos creados mediante typedef (structs, enums, unions) deben identificarse con sufijo '_t' (o prefijo 't_').",
        "ejemplo_correcto": "typedef struct nodo nodo_t;\ntypedef enum estado estado_t;",
        "ejemplo_incorrecto": "typedef struct nodo Nodo;",
        "autofix": "No",
    },
    "0x3005h": {
        "codigo": "0x3005h",
        "titulo": "Minimizá el uso de múltiples niveles de indirección (***ptr)",
        "descripcion": "Evitar punteros triples o niveles de indirección innecesariamente complejos.",
        "ejemplo_correcto": "int *obtener_datos(size_t *tamano);",
        "ejemplo_incorrecto": "void obtener_datos(int ***ptr_datos);",
        "autofix": "No",
    },
    "0x3006h": {
        "codigo": "0x3006h",
        "titulo": "Documentá la propiedad de los recursos al utilizar punteros",
        "descripcion": "Indicar explícitamente en el contrato quién es responsable de liberar la memoria.",
        "ejemplo_correcto": "/** @return Puntero asignado. El llamador debe liberar con free(). */",
        "ejemplo_incorrecto": "char *crear_cadena();",
        "autofix": "No",
    },
    "0x3007h": {
        "codigo": "0x3007h",
        "titulo": "Argumentos puntero de solo lectura deben ser const",
        "descripcion": "Calificar con const los punteros cuyos datos apuntados no son modificados por la función.",
        "ejemplo_correcto": "void imprimir_texto(const char *cadena);",
        "ejemplo_incorrecto": "void imprimir_texto(char *cadena);",
        "autofix": "No",
    },
    "0x3008h": {
        "codigo": "0x3008h",
        "titulo": "Punteros nulos deben ser inicializados y comparados con NULL",
        "descripcion": "Usar explícitamente NULL en lugar del literal 0 para punteros.",
        "ejemplo_correcto": "int *ptr = NULL;\nif (ptr == NULL) { ... }",
        "ejemplo_incorrecto": "int *ptr = 0;\nif (ptr == 0) { ... }",
        "autofix": "No",
    },
    "0x3009h": {
        "codigo": "0x3009h",
        "titulo": "Documentá explícitamente los casos en que una función puede retornar NULL",
        "descripcion": "Aclarar en la documentación si el retorno NULL indica error o fin de búsqueda.",
        "ejemplo_correcto": "/** @return Puntero al elemento, o NULL si no existe. */",
        "ejemplo_incorrecto": "nodo_t *buscar(int id);",
        "autofix": "No",
    },
    "0x300Ah": {
        "codigo": "0x300Ah",
        "titulo": "Utilizá cast explícito al convertir tipos de punteros",
        "descripcion": "Evitar conversiones implícitas incompatibles entre diferentes tipos de punteros.",
        "ejemplo_correcto": "int *ptr = (int *)mem;",
        "ejemplo_incorrecto": "int *ptr = mem;",
        "autofix": "No",
    },
    "0x300Bh": {
        "codigo": "0x300Bh",
        "titulo": "Usá siempre sizeof en asignaciones dinámicas (prefiriendo sizeof(*ptr))",
        "descripcion": "Evitar tamaños fijos calculados a mano en malloc/calloc.",
        "ejemplo_correcto": "ptr = malloc(sizeof(*ptr));",
        "ejemplo_incorrecto": "ptr = malloc(4);",
        "autofix": "No",
    },
    "0x300Ch": {
        "codigo": "0x300Ch",
        "titulo": "Verificá siempre los límites de los arreglos antes de acceder a sus elementos",
        "descripcion": "Validar índices de arreglos para evitar desbordamientos de búfer (out-of-bounds).",
        "ejemplo_correcto": "if (indice >= 0 && indice < TAMANO) { arr[indice] = x; }",
        "ejemplo_incorrecto": "arr[indice] = x; // Sin chequear si indice < TAMANO",
        "autofix": "No",
    },
    "0x300Dh": {
        "codigo": "0x300Dh",
        "titulo": "Utilizá enum o constantes en lugar de números mágicos",
        "descripcion": "No utilizar literales numéricos sin contexto en el cuerpo del código (distintos de 0, 1, 2, -1). Definir constantes con #define o enum.",
        "ejemplo_correcto": "#define MAX_INTENTOS 5\nfor (int i = 0; i < MAX_INTENTOS; i++)",
        "ejemplo_incorrecto": "for (int i = 0; i < 5; i++) // ¿Qué significa 5?",
        "autofix": "No",
    },
    "0x300Eh": {
        "codigo": "0x300Eh",
        "titulo": "Documentá el comportamiento de las funciones ante punteros nulos",
        "descripcion": "Especificar si una función tolera parámetros NULL o aborta con aserción.",
        "ejemplo_correcto": "/** @param ptr Puntero al recurso (no debe ser NULL). */",
        "ejemplo_incorrecto": "void procesar(nodo_t *ptr);",
        "autofix": "No",
    },
    "0x300Fh": {
        "codigo": "0x300Fh",
        "titulo": "Liberá la memoria en el orden inverso a su asignación (deep free)",
        "descripcion": "Liberar los miembros dinámicos antes de liberar la estructura contenedora.",
        "ejemplo_correcto": "free(nodo->nombre);\nfree(nodo);",
        "ejemplo_incorrecto": "free(nodo);\n// nodo->nombre quedó huérfano (leak)",
        "autofix": "No",
    },
    "0x3010h": {
        "codigo": "0x3010h",
        "titulo": "Variables de tamaños o índices deben ser de tipo size_t",
        "descripcion": "Utilizar size_t en lugar de int con signo para longitudes e iteradores de arreglos.",
        "ejemplo_correcto": "size_t longitud = strlen(cadena);",
        "ejemplo_incorrecto": "int longitud = strlen(cadena);",
        "autofix": "No",
    },
    "0x3011h": {
        "codigo": "0x3011h",
        "titulo": "Si una función recibe un puntero genérico de solo lectura, usar const void*",
        "descripcion": "Firmar funciones con const void* cuando no se modifiquen los bytes leídos.",
        "ejemplo_correcto": "void imprimir_hex(const void *buffer, size_t n);",
        "ejemplo_incorrecto": "void imprimir_hex(void *buffer, size_t n);",
        "autofix": "No",
    },
    "0x0035h": {
        "codigo": "0x0035h",
        "titulo": "Diseñá los Tipos de Datos Abstractos utilizando punteros opacos",
        "descripcion": "Ocultar los detalles de implementación de structs en archivos .h mediante punteros incompletos.",
        "ejemplo_correcto": "typedef struct lista_t lista_t; // En lista.h",
        "ejemplo_incorrecto": "struct lista_t { nodo_t *cabeza; }; // En lista.h expone campos internos",
        "autofix": "No",
    },
    "0x0036h": {
        "codigo": "0x0036h",
        "titulo": "Asigná NULL al puntero tras liberar un recurso opaco",
        "descripcion": "Asignar NULL al puntero en el cliente tras destruir un TDA para prevenir accesos inválidos.",
        "ejemplo_correcto": "lista_destruir(mi_lista);\nmi_lista = NULL;",
        "ejemplo_incorrecto": "lista_destruir(mi_lista);",
        "autofix": "No",
    },

    # 0x40XXh: Gestión de Archivos y Errores
    "0x4001h": {
        "codigo": "0x4001h",
        "titulo": "Manejá correctamente la apertura y cierre de archivos",
        "descripcion": "Validar if (archivo == NULL) tras fopen y asegurar el cierre con fclose.",
        "ejemplo_correcto": "FILE *f = fopen(\"datos.txt\", \"r\");\nif (f == NULL) return -1;\n...\nfclose(f);",
        "ejemplo_incorrecto": "FILE *f = fopen(\"datos.txt\", \"r\");\nfread(buf, 1, 10, f); // Si f es NULL rompe",
        "autofix": "No",
    },
    "0x4002h": {
        "codigo": "0x4002h",
        "titulo": "Validá los retornos de lectura y escritura de archivos",
        "descripcion": "Verificar los valores de retorno de fread, fwrite, fgets, fscanf.",
        "ejemplo_correcto": "size_t leidos = fread(buf, 1, 100, f);\nif (leidos < 100) { ... }",
        "ejemplo_incorrecto": "fread(buf, 1, 100, f); // Sin verificar si leyó",
        "autofix": "No",
    },
    "0x4003h": {
        "codigo": "0x4003h",
        "titulo": "Utilizá errno, perror y strerror para reportar fallos",
        "descripcion": "Diagnosticar fallos de archivos mediante perror o strerror(errno).",
        "ejemplo_correcto": "if (f == NULL) { perror(\"Error al abrir archivo\"); }",
        "ejemplo_incorrecto": "if (f == NULL) { printf(\"Error\\n\"); }",
        "autofix": "No",
    },
    "0x4004h": {
        "codigo": "0x4004h",
        "titulo": "Asegurá la simetría de recursos al abrir y cerrar archivos",
        "descripcion": "Abrir y cerrar descriptores de archivos dentro del mismo nivel de abstracción funcional.",
        "ejemplo_correcto": "void procesar() { FILE *f = fopen(...); ... fclose(f); }",
        "ejemplo_incorrecto": "FILE *f = fopen(...); delegar(f); // Nadie cierra f",
        "autofix": "No",
    },
    "0x4005h": {
        "codigo": "0x4005h",
        "titulo": "Evitá offsets fijos codificados a mano sin validar dimensiones",
        "descripcion": "Comprobar el tamaño real del archivo antes de posicionar punteros con fseek.",
        "ejemplo_correcto": "if (offset < tamano_archivo) { fseek(f, offset, SEEK_SET); }",
        "ejemplo_incorrecto": "fseek(f, 1000, SEEK_SET);",
        "autofix": "No",
    },

    # 0x50XXh: Compilación y Buenas Prácticas
    "0x5001h": {
        "codigo": "0x5001h",
        "titulo": "Arreglos estáticos con tamaño fijo en compilación (prohibido VLA)",
        "descripcion": "Los arreglos de longitud variable (int arr[n]) están prohibidos; usar constantes (#define) o malloc.",
        "ejemplo_correcto": "#define TAMANO 100\nint arr[TAMANO];",
        "ejemplo_incorrecto": "int n = 100;\nint arr[n]; // VLA prohibido",
        "autofix": "No",
    },
    "0x5002h": {
        "codigo": "0x5002h",
        "titulo": "Desarrollá y compilá siempre con todas las advertencias activadas",
        "descripcion": "Compilar con -Wall -Wextra -Werror -pedantic para detectar anomalías tempranas.",
        "ejemplo_correcto": "CFLAGS = -Wall -Wextra -Werror -pedantic -std=c11",
        "ejemplo_incorrecto": "gcc main.c -o app",
        "autofix": "No",
    },
    "0x5003h": {
        "codigo": "0x5003h",
        "titulo": "Utilizá guardas de inclusión en todos los archivos de cabecera",
        "descripcion": "Todo archivo de cabecera (.h) debe incluir guardas de preprocesador (#ifndef ARCHIVO_H / #define ARCHIVO_H / #endif) o #pragma once.",
        "ejemplo_correcto": "#ifndef LISTA_H\n#define LISTA_H\n...\n#endif /* LISTA_H */",
        "ejemplo_incorrecto": "Archivo lista.h sin guardas de inclusión.",
        "autofix": "Sí",
    },
    "0x5004h": {
        "codigo": "0x5004h",
        "titulo": "Todas las operaciones con cadenas deben ser seguras",
        "descripcion": "Utilizar snprintf o strncpy en lugar de strcpy/strcat sin límite de tamaño para prevenir buffer overflows.",
        "ejemplo_correcto": "snprintf(dest, sizeof(dest), \"%s\", orig);",
        "ejemplo_incorrecto": "strcpy(dest, orig);\nstrcat(dest, extra);",
        "autofix": "No",
    },
    "0x5005h": {
        "codigo": "0x5005h",
        "titulo": "Organizá la estructura de tus archivos .c de forma estándar",
        "descripcion": "Estructurar los archivos con includes, defines, typedefs, prototipos y funciones en orden predecible.",
        "ejemplo_correcto": "1. #includes\n2. #defines\n3. typedefs\n4. Prototipos static\n5. Implementaciones",
        "ejemplo_incorrecto": "Declarar funciones antes de includes o mezclar defines en el medio del archivo.",
        "autofix": "No",
    },
    "0x5006h": {
        "codigo": "0x5006h",
        "titulo": "Preferí fgets sobre gets y scanf para leer cadenas",
        "descripcion": "La función gets() está prohibida y scanf(\"%s\") no valida desbordamientos.",
        "ejemplo_correcto": "fgets(buffer, sizeof(buffer), stdin);",
        "ejemplo_incorrecto": "gets(buffer);\nscanf(\"%s\", buffer);",
        "autofix": "No",
    },

    # 0x00XXh complementarios: serie GAFF06x y GAFF07x
    "0x000Dh": {
        "codigo": "0x000Dh",
        "titulo": "No dejes código comentado (dead code) en los archivos fuente",
        "descripcion": "El código comentado ensucia el archivo y confunde al lector: debe eliminarse. El historial de cambios pertenece al control de versiones, no a los fuentes.",
        "ejemplo_correcto": "int total = calcular_total(precio);",
        "ejemplo_incorrecto": "// int total = calcular_total_viejo(precio);\nint total = calcular_total(precio);",
        "autofix": "No",
    },
    "0x000Eh": {
        "codigo": "0x000Eh",
        "titulo": "Los nombres de funciones deben usar snake_case estricto en minúsculas",
        "descripcion": "Todas las funciones deben nombrarse en snake_case en minúsculas, sin mezclar camelCase ni PascalCase.",
        "ejemplo_correcto": "int procesar_vector(int *vec, size_t n);",
        "ejemplo_incorrecto": "int procesarVector(int *vec, size_t n);",
        "autofix": "No",
    },
    "0x000Fh": {
        "codigo": "0x000Fh",
        "titulo": "Evitá comentarios obvios, redundantes o vacíos",
        "descripcion": "Los comentarios deben explicar la razón o justificación del algoritmo, no repetir la sintaxis obvia ni estar vacíos (//, /* */).",
        "ejemplo_correcto": "// Ajustamos el offset por alineación de 64 bits\nptr += 8;",
        "ejemplo_incorrecto": "i++; // incrementa i en uno\n//\n/* TODO */",
        "autofix": "Sí",
    },
    "0x0010h": {
        "codigo": "0x0010h",
        "titulo": "Control de longitud máxima de archivos de código (máx 500 líneas)",
        "descripcion": "Los archivos .c no deben superar las 500 líneas para favorecer la modularización y cohesión en TDAs.",
        "ejemplo_correcto": "modulo_pila.c (120 líneas) y modulo_cola.c (140 líneas)",
        "ejemplo_incorrecto": "todo_junto.c (950 líneas)",
        "autofix": "No",
    },
    "0x0011h": {
        "codigo": "0x0011h",
        "titulo": "En archivos .c la inclusión de la cabecera propia debe figurar en primer lugar",
        "descripcion": "En modulo.c, '#include \"modulo.h\"' debe ser la primera inclusión de usuario para asegurar que el header sea autosuficiente.",
        "ejemplo_correcto": "#include \"mi_modulo.h\"\n#include <stdio.h>",
        "ejemplo_incorrecto": "#include <stdio.h>\n#include \"otra_cosa.h\"\n#include \"mi_modulo.h\"",
        "autofix": "No",
    },
    "0x0012h": {
        "codigo": "0x0012h",
        "titulo": "Las variables globales deben ser declaradas como static o usar prefijo g_",
        "descripcion": "Las variables con alcance de archivo deben restringirse con static o usar explícitamente el prefijo g_ para visibilizar el acoplamiento global.",
        "ejemplo_correcto": "static int g_contador_llamadas = 0;",
        "ejemplo_incorrecto": "int total_acumulado = 0; // variable global no static",
        "autofix": "No",
    },
    "0x0037h": {
        "codigo": "0x0037h",
        "titulo": "Evitá identificadores genéricos con sufijo numérico (numero1, num_1, etc.)",
        "descripcion": "Los identificadores genéricos seguidos de un número (como 'numero1', 'numero_1', 'num1', 'var1', 'dato1', etc.) denotan una elección pobre de nombres y falta de abstracción. Usá nombres que reflejen el rol semántico específico o utilizá un arreglo si representan una colección.",
        "ejemplo_correcto": "int dividendo = 10, divisor = 2;\nint valores[2] = {10, 2};",
        "ejemplo_incorrecto": "int numero1 = 10, numero2 = 2;\nint num_1 = 10, num_2 = 2;",
        "autofix": "No",
    },
    "0x0013h": {
        "codigo": "0x0013h",
        "alias": "GAFF_0x0013h",
        "titulo": "Las macros #define deben nombrarse en MAYUSCULAS_SNAKE_CASE",
        "categoria": "Sintaxis Básica y Nomenclatura (0x00XX)",
        "archivo_apunte": "0_sintaxis.md",
        "descripcion": "Las constantes y macros de preprocesador #define deben escribirse en mayúsculas sostenidas para distinguirlas visualmente de funciones e identificadores ordinarios.",
        "ejemplo_correcto": "#define BUFFER_MAX 1024",
        "ejemplo_incorrecto": "#define buffer_max 1024",
        "autofix": "No",
    },
    "0x100Ah": {
        "codigo": "0x100Ah",
        "alias": "GAFF_0x100Ah",
        "titulo": "Prohibición de asignaciones simples dentro de condiciones lógicas",
        "categoria": "Estructuras de Control y Lazos (0x10XX)",
        "archivo_apunte": "1_control.md",
        "descripcion": "No realizar asignaciones con '=' dentro de expresiones de control if o while. Usar '==' para comparar o evaluar la asignación en una línea previa.",
        "ejemplo_correcto": "if (estado == ACTIVO) { ... }",
        "ejemplo_incorrecto": "if (estado = ACTIVO) { ... }",
        "autofix": "No",
    },
    "0x100Bh": {
        "codigo": "0x100Bh",
        "alias": "GAFF_0x100Bh",
        "titulo": "Prohibición de estructuras de control con cuerpo vacío (if (...);)",
        "categoria": "Estructuras de Control y Lazos (0x10XX)",
        "archivo_apunte": "1_control.md",
        "descripcion": "Un punto y coma inmediatamente tras el paréntesis de un if o while crea un bloque nulo y casi siempre representa un error lógico grave.",
        "ejemplo_correcto": "if (x > 0) {\n    procesar(x);\n}",
        "ejemplo_incorrecto": "if (x > 0);\n{\n    procesar(x);\n}",
        "autofix": "No",
    },
    "0x200Bh": {
        "codigo": "0x200Bh",
        "alias": "GAFF_0x200Bh",
        "titulo": "Modularización: una función no debe exceder 4 parámetros de entrada",
        "categoria": "Funciones y Modularización (0x20XX)",
        "archivo_apunte": "2_funciones.md",
        "descripcion": "Las funciones que requieren más de 4 argumentos deben empaquetar sus parámetros en estructuras (struct) o TDAs para reducir el acoplamiento.",
        "ejemplo_correcto": "void crear_usuario(const struct config_usuario_t *cfg);",
        "ejemplo_incorrecto": "void crear_usuario(const char *nom, const char *ape, int edad, int dni, const char *mail);",
        "autofix": "No",
    },
    "0x3012h": {
        "codigo": "0x3012h",
        "alias": "GAFF_0x3012h",
        "titulo": "Prohibición de aritmética de punteros sobre void*",
        "categoria": "Punteros y Gestión de Memoria (0x30XX)",
        "archivo_apunte": "3_punteros.md",
        "descripcion": "La aritmética sobre void* es inválida en C estándar ANSI/ISO ya que sizeof(void) no está definido. Debe castearse a char* o uint8_t*.",
        "ejemplo_correcto": "void *sig = (char *)ptr + salto;",
        "ejemplo_incorrecto": "void *sig = ptr + salto;",
        "autofix": "No",
    },
    "0x3015h": {
        "codigo": "0x3015h",
        "alias": "GAFF_0x3015h",
        "titulo": "Reallocación segura: no sobreescribir el puntero original directamente",
        "categoria": "Punteros y Gestión de Memoria (0x30XX)",
        "archivo_apunte": "3_punteros.md",
        "descripcion": "Asignar 'p = realloc(p, size)' causa fuga de memoria si realloc() falla y retorna NULL. Utilizar siempre una variable temporal.",
        "ejemplo_correcto": "int *tmp = realloc(p, nuevo_tam);\nif (tmp != NULL) p = tmp;",
        "ejemplo_incorrecto": "p = realloc(p, nuevo_tam);",
        "autofix": "No",
    },
    "0x4007h": {
        "codigo": "0x4007h",
        "alias": "GAFF_0x4007h",
        "titulo": "Prohibición de rutas absolutas hardcodeadas en llamadas de archivo",
        "categoria": "Gestión de Archivos y Errores (0x40XX)",
        "archivo_apunte": "4_archivos.md",
        "descripcion": "No incluir rutas locales absolutas fijas (/home/..., C:\\\\...) en fopen(). Usar rutas relativas o argumentos recibidos por la aplicación.",
        "ejemplo_correcto": "FILE *f = fopen(\"datos.csv\", \"r\");",
        "ejemplo_incorrecto": "FILE *f = fopen(\"/home/usuario/datos.csv\", \"r\");",
        "autofix": "No",
    },
    "0x5007h": {
        "codigo": "0x5007h",
        "alias": "GAFF_0x5007h",
        "titulo": "Inclusiones redundantes o duplicadas de la misma cabecera #include",
        "categoria": "Compilación y Buenas Prácticas de Ingeniería (0x50XX)",
        "archivo_apunte": "5_buenas_practicas.md",
        "descripcion": "No incluir dos veces el mismo archivo de cabecera en una misma unidad de traducción.",
        "ejemplo_correcto": "#include <stdio.h>\n#include <stdlib.h>",
        "ejemplo_incorrecto": "#include <stdio.h>\n#include <stdlib.h>\n#include <stdio.h>",
        "autofix": "Sí",
    },
    "0x5008h": {
        "codigo": "0x5008h",
        "alias": "GAFF_0x5008h",
        "titulo": "Prohibición de funciones obsoletas o inseguras (gets, atoi)",
        "categoria": "Compilación y Buenas Prácticas de Ingeniería (0x50XX)",
        "archivo_apunte": "5_buenas_practicas.md",
        "descripcion": "El uso de gets() está estrictamente prohibido (eliminado en C11). atoi() no detecta errores de conversión; debe utilizarse strtol().",
        "ejemplo_correcto": "fgets(buf, sizeof(buf), stdin);\nlong val = strtol(str, &fin, 10);",
        "ejemplo_incorrecto": "gets(buf);\nint val = atoi(str);",
        "autofix": "No",
    },
    "0x5009h": {
        "codigo": "0x5009h",
        "alias": "GAFF_0x5009h",
        "titulo": "Prohibición de división entera no intencional asignada a flotantes",
        "categoria": "Compilación y Buenas Prácticas de Ingeniería (0x50XX)",
        "archivo_apunte": "5_buenas_practicas.md",
        "descripcion": "Asignar el resultado de una división entre enteros a un float o double (ej: double d = 1 / 2) trunca a cero antes de la asignación. Usar literales flotantes (1.0 / 2).",
        "ejemplo_correcto": "double tasa = 1.0 / 2.0;",
        "ejemplo_incorrecto": "double tasa = 1 / 2;",
        "autofix": "No",
    },
    "0x0014h": {
        "codigo": "0x0014h",
        "alias": "GAFF_0x0014h",
        "titulo": "Prohibición de identificadores con caracteres no ASCII (acentos, ñ)",
        "categoria": "Sintaxis Básica y Nomenclatura (0x00XX)",
        "archivo_apunte": "0_sintaxis.md",
        "descripcion": "Los nombres de variables, funciones y tipos deben restringirse al conjunto ASCII estándar [a-zA-Z0-9_]. El uso de tildes o 'ñ' compromete la portabilidad entre compiladores y sistemas operativos.",
        "ejemplo_correcto": "int anio = 2026;\nfloat numero = 3.14;",
        "ejemplo_incorrecto": "int año = 2026;\nfloat número = 3.14;",
        "autofix": "No",
    },
    "0x0015h": {
        "codigo": "0x0015h",
        "alias": "GAFF_0x0015h",
        "titulo": "Prohibición del operador coma para encadenar sentencias independientes",
        "categoria": "Sintaxis Básica y Nomenclatura (0x00XX)",
        "archivo_apunte": "0_sintaxis.md",
        "descripcion": "No encadenar asignaciones o sentencias mediante el operador coma (ej: x = 1, y = 2;). Cada sentencia debe residir en una línea independiente finalizada en punto y coma.",
        "ejemplo_correcto": "x = 1;\ny = 2;",
        "ejemplo_incorrecto": "x = 1, y = 2;",
        "autofix": "No",
    },
    "0x100Ch": {
        "codigo": "0x100Ch",
        "alias": "GAFF_0x100Ch",
        "titulo": "Exigencia de break explícito o comentario de fallthrough en bloques switch case",
        "categoria": "Estructuras de Control y Lazos (0x10XX)",
        "archivo_apunte": "1_control.md",
        "descripcion": "Cada cláusula 'case' no vacía en una instrucción 'switch' debe finalizar con 'break;' o 'return;'. Si la caída es deliberada, debe documentarse con '// fallthrough'.",
        "ejemplo_correcto": "case 1:\n    procesar();\n    break;\ncase 2:\n    return;",
        "ejemplo_incorrecto": "case 1:\n    procesar();\ncase 2:\n    otro();",
        "autofix": "No",
    },
    "0x100Dh": {
        "codigo": "0x100Dh",
        "alias": "GAFF_0x100Dh",
        "titulo": "Prohibición de modificar la variable de control dentro del cuerpo del for",
        "categoria": "Estructuras de Control y Lazos (0x10XX)",
        "archivo_apunte": "1_control.md",
        "descripcion": "La variable de control de un lazo 'for' debe evolucionar exclusivamente en la cláusula de incremento. Modificarla en el cuerpo ofusca la condición de parada; preferí 'while'.",
        "ejemplo_correcto": "for (int i = 0; i < n; i++) {\n    printf(\"%d\", i);\n}",
        "ejemplo_incorrecto": "for (int i = 0; i < n; i++) {\n    if (cond) i += 2;\n}",
        "autofix": "No",
    },
    "0x200Ch": {
        "codigo": "0x200Ch",
        "alias": "GAFF_0x200Ch",
        "titulo": "Prohibición de retornar la dirección de una variable local de stack",
        "categoria": "Funciones y Modularización (0x20XX)",
        "archivo_apunte": "2_funciones.md",
        "descripcion": "Retornar un puntero a una variable local de stack (&variable) genera un puntero colgante (dangling pointer) ya que el marco de activación se destruye al finalizar la función.",
        "ejemplo_correcto": "int *crear(void) {\n    int *p = malloc(sizeof(int));\n    return p;\n}",
        "ejemplo_incorrecto": "int *crear(void) {\n    int x = 10;\n    return &x;\n}",
        "autofix": "No",
    },
    "0x3013h": {
        "codigo": "0x3013h",
        "alias": "GAFF_0x3013h",
        "titulo": "Asignación de memoria con sizeof sobre puntero en lugar del tipo apuntado",
        "categoria": "Punteros y Gestión de Memoria (0x30XX)",
        "archivo_apunte": "3_punteros.md",
        "descripcion": "Al alocar memoria dinámica con 'ptr = malloc(...)', debe usarse 'sizeof(*ptr)' o 'sizeof(tipo)'. Usar 'sizeof(ptr)' reserva solo el tamaño del puntero (4 u 8 bytes) provocando desbordamientos.",
        "ejemplo_correcto": "int *arr = malloc(10 * sizeof(*arr));",
        "ejemplo_incorrecto": "int *arr = malloc(10 * sizeof(arr));",
        "autofix": "No",
    },
    "0x3014h": {
        "codigo": "0x3014h",
        "alias": "GAFF_0x3014h",
        "titulo": "Prohibición de doble liberación de memoria (double free) sobre el mismo puntero",
        "categoria": "Punteros y Gestión de Memoria (0x30XX)",
        "archivo_apunte": "3_punteros.md",
        "descripcion": "Invocar 'free(ptr)' dos veces consecutivas sobre el mismo puntero corrompe el heap del asignador de memoria (glibc / jemalloc) y provoca abortos inmediatos (SIGABRT).",
        "ejemplo_correcto": "free(ptr);\nptr = NULL;",
        "ejemplo_incorrecto": "free(ptr);\nfree(ptr);",
        "autofix": "No",
    },
    "0x4006h": {
        "codigo": "0x4006h",
        "alias": "GAFF_0x4006h",
        "titulo": "Prohibición del antipatrón while (!feof(f)) para control de fin de archivo",
        "categoria": "Gestión de Archivos y Errores (0x40XX)",
        "archivo_apunte": "4_archivos.md",
        "descripcion": "La función 'feof()' solo retorna verdadero DESPUÉS de que una operación de lectura previa haya fallado al toparse con el fin de archivo. Usarla en la cabecera procesa el último registro dos veces.",
        "ejemplo_correcto": "while (fgets(buf, sizeof(buf), f) != NULL) {\n    procesar(buf);\n}",
        "ejemplo_incorrecto": "while (!feof(f)) {\n    fgets(buf, sizeof(buf), f);\n    procesar(buf);\n}",
        "autofix": "No",
    },
    "0x500Ah": {
        "codigo": "0x500Ah",
        "alias": "GAFF_0x500Ah",
        "titulo": "Protección obligatoria de parámetros en macros funcionales mediante paréntesis",
        "categoria": "Compilación y Buenas Prácticas de Ingeniería (0x50XX)",
        "archivo_apunte": "5_buenas_practicas.md",
        "descripcion": "Los parámetros en el cuerpo de una macro funcional (#define CUADRADO(x) ...) deben estar siempre encerrados entre paréntesis '((x) * (x))' para prevenir anomalías por precedencia de operadores.",
        "ejemplo_correcto": "#define MULT(a, b) ((a) * (b))",
        "ejemplo_incorrecto": "#define MULT(a, b) a * b",
        "autofix": "No",
    },
    "0x500Bh": {
        "codigo": "0x500Bh",
        "alias": "GAFF_0x500Bh",
        "titulo": "Inclusión obligatoria de cabeceras estándar para funciones de la biblioteca C",
        "categoria": "Compilación y Buenas Prácticas de Ingeniería (0x50XX)",
        "archivo_apunte": "5_buenas_practicas.md",
        "descripcion": "Toda invocación a funciones estándar de C requiere la inclusión explícita de su respectiva cabecera: printf/scanf (<stdio.h>), malloc/free/exit (<stdlib.h>), strcmp/strlen (<string.h>), assert (<assert.h>).",
        "ejemplo_correcto": "#include <stdio.h>\nint main(void) {\n    printf(\"hola\");\n    return 0;\n}",
        "ejemplo_incorrecto": "int main(void) {\n    printf(\"hola\");\n    return 0;\n}",
        "autofix": "No",
    },
    "0x0016h": {
        "codigo": "0x0016h",
        "alias": "GAFF_0x0016h",
        "titulo": "Prohibición de identificadores que colisionen con palabras clave o tipos estándar",
        "categoria": "Sintaxis Básica y Nomenclatura (0x00XX)",
        "archivo_apunte": "0_sintaxis.md",
        "descripcion": "No utilizar palabras reservadas o tipos estándar de C99/C11/POSIX (restrict, inline, bool, true, false, nullptr, alignas) como nombres de variables o parámetros.",
        "ejemplo_correcto": "bool es_valido = true;\nint limite = 10;",
        "ejemplo_incorrecto": "int bool = 1;\nint restrict = 0;",
        "autofix": "No",
    },
    "0x0017h": {
        "codigo": "0x0017h",
        "alias": "GAFF_0x0017h",
        "titulo": "Prohibición de notación húngara o prefijos redundantes de tipo en identificadores",
        "categoria": "Sintaxis Básica y Nomenclatura (0x00XX)",
        "archivo_apunte": "0_sintaxis.md",
        "descripcion": "Evitar prefijos redundantes como 'int_', 'float_', 'str_', 'arr_' o notación húngara en nombres de variables. El tipo ya está determinado por el lenguaje.",
        "ejemplo_correcto": "int edad = 20;\nchar *nombre = \"Ana\";",
        "ejemplo_incorrecto": "int int_edad = 20;\nchar *str_nombre = \"Ana\";",
        "autofix": "No",
    },
    "0x100Eh": {
        "codigo": "0x100Eh",
        "alias": "GAFF_0x100Eh",
        "titulo": "Prohibición de condiciones constantes o tautológicas en sentencias if",
        "categoria": "Estructuras de Control y Lazos (0x10XX)",
        "archivo_apunte": "1_control.md",
        "descripcion": "No utilizar literales booleanos o enteros constantes (1, 0, true, false) como condición en sentencias if; denota código de depuración residual o ramificación muerta.",
        "ejemplo_correcto": "if (activo) { ... }",
        "ejemplo_incorrecto": "if (1) { ... }\nif (false) { ... }",
        "autofix": "No",
    },
    "0x100Fh": {
        "codigo": "0x100Fh",
        "alias": "GAFF_0x100Fh",
        "titulo": "Prohibición de condiciones de parada compuestas complejas en lazos for",
        "categoria": "Estructuras de Control y Lazos (0x10XX)",
        "archivo_apunte": "1_control.md",
        "descripcion": "La cláusula de condición del lazo for debe ser una comprobación simple de cota (i < n). Si requiere múltiples condiciones lógicas (&& / ||), utilizá un lazo while.",
        "ejemplo_correcto": "for (int i = 0; i < n; i++) { ... }",
        "ejemplo_incorrecto": "for (int i = 0; i < n && !encontrado && limite > 0; i++) { ... }",
        "autofix": "No",
    },
    "0x200Eh": {
        "codigo": "0x200Eh",
        "alias": "GAFF_0x200Eh",
        "titulo": "Declaración explícita de (void) en funciones que no reciben parámetros",
        "categoria": "Funciones y Modularización (0x20XX)",
        "archivo_apunte": "2_funciones.md",
        "descripcion": "En lenguaje C, una función declarada como 'f()' acepta cualquier número de argumentos sin verificación de tipos. Debe declararse explícitamente como 'f(void)'.",
        "ejemplo_correcto": "void limpiar_pantalla(void);",
        "ejemplo_incorrecto": "void limpiar_pantalla();",
        "autofix": "Sí",
    },
    "0x200Fh": {
        "codigo": "0x200Fh",
        "alias": "GAFF_0x200Fh",
        "titulo": "Calificador static obligatorio en funciones auxiliares privadas de archivo",
        "categoria": "Funciones y Modularización (0x20XX)",
        "archivo_apunte": "2_funciones.md",
        "descripcion": "Las funciones auxiliares internas de un archivo .c que no forman parte de la interfaz pública (.h) deben declararse como 'static' para encapsular su enlace y visibilidad.",
        "ejemplo_correcto": "static int calcular_checksum(const char *buf);",
        "ejemplo_incorrecto": "int calcular_checksum(const char *buf);",
        "autofix": "No",
    },
    "0x3016h": {
        "codigo": "0x3016h",
        "alias": "GAFF_0x3016h",
        "titulo": "Prohibición de desreferencia directa de memoria dinámica sin check a NULL previo",
        "categoria": "Punteros y Gestión de Memoria (0x30XX)",
        "archivo_apunte": "3_punteros.md",
        "descripcion": "Desreferenciar un puntero inmediatamente tras invocar malloc/calloc sin mediar un bloque condicional que verifique contra NULL arriesga segfaults directos ante escasez de memoria.",
        "ejemplo_correcto": "int *p = malloc(sizeof(int));\nif (p == NULL) return;\n*p = 10;",
        "ejemplo_incorrecto": "int *p = malloc(sizeof(int));\n*p = 10;",
        "autofix": "No",
    },
    "0x3017h": {
        "codigo": "0x3017h",
        "alias": "GAFF_0x3017h",
        "titulo": "Prohibición de utilizar free() como valor o dentro de expresiones compuestas",
        "categoria": "Punteros y Gestión de Memoria (0x30XX)",
        "archivo_apunte": "3_punteros.md",
        "descripcion": "La función free() retorna void y tiene como único propósito la liberación de memoria. No debe asignarse a variables ni formar parte de operaciones aritméticas o condicionales.",
        "ejemplo_correcto": "free(ptr);\nptr = NULL;",
        "ejemplo_incorrecto": "int res = (free(ptr), 0);",
        "autofix": "No",
    },
    "0x4008h": {
        "codigo": "0x4008h",
        "alias": "GAFF_0x4008h",
        "titulo": "Validación obligatoria del valor de retorno de fclose() en modo escritura",
        "categoria": "Gestión de Archivos y Errores (0x40XX)",
        "archivo_apunte": "4_archivos.md",
        "descripcion": "Al cerrar flujos de archivo abiertos para escritura (\"w\", \"a\", \"wb\"), fclose() puede fallar al vaciar el búfer del sistema operativo. Debe verificarse que retorne distinto de EOF.",
        "ejemplo_correcto": "FILE *f = fopen(\"log.txt\", \"w\");\n...\nif (fclose(f) == EOF) { perror(\"Error\"); }",
        "ejemplo_incorrecto": "FILE *f = fopen(\"log.txt\", \"w\");\n...\nfclose(f); // retorno ignorado en archivo de salida",
        "autofix": "No",
    },
    "0x4009h": {
        "codigo": "0x4009h",
        "alias": "GAFF_0x4009h",
        "titulo": "Prohibición de anidar llamadas a fopen() directamente dentro de funciones de E/S",
        "categoria": "Gestión de Archivos y Errores (0x40XX)",
        "archivo_apunte": "4_archivos.md",
        "descripcion": "Llamar a fopen() dentro del paso de parámetros de fread/fscanf impide comprobar si el retorno fue NULL y genera fugas de recursos al no existir puntero para fclose().",
        "ejemplo_correcto": "FILE *f = fopen(\"data.txt\", \"r\");\nif (f) { fscanf(f, \"%d\", &x); fclose(f); }",
        "ejemplo_incorrecto": "fscanf(fopen(\"data.txt\", \"r\"), \"%d\", &x); // anidamiento inseguro",
        "autofix": "No",
    },
    "0x500Ch": {
        "codigo": "0x500Ch",
        "alias": "GAFF_0x500Ch",
        "titulo": "Prohibición de inclusión directa de archivos de código fuente C (.c)",
        "categoria": "Compilación y Buenas Prácticas de Ingeniería (0x50XX)",
        "archivo_apunte": "5_buenas_practicas.md",
        "descripcion": "Nunca incluir archivos con extensión '.c' mediante '#include'. Viola los principios de compilación separada y produce errores de símbolos duplicados en el enlazador (ld).",
        "ejemplo_correcto": "#include \"modulo.h\"",
        "ejemplo_incorrecto": "#include \"modulo.c\"",
        "autofix": "No",
    },
    "0x500Dh": {
        "codigo": "0x500Dh",
        "alias": "GAFF_0x500Dh",
        "titulo": "Prohibición de redefinir palabras clave o tipos primitivos de C con #define",
        "categoria": "Compilación y Buenas Prácticas de Ingeniería (0x50XX)",
        "archivo_apunte": "5_buenas_practicas.md",
        "descripcion": "Está estrictamente prohibido alterar la semántica básica del lenguaje mediante macros que redefinan palabras clave como 'if', 'for', 'int', 'return', etc.",
        "ejemplo_correcto": "#define BOOLEAN_TRUE 1",
        "ejemplo_incorrecto": "#define if while\n#define int long",
        "autofix": "No",
    },
    "0x0018h": {
        "codigo": "0x0018h",
        "alias": "GAFF_0x0018h",
        "titulo": "Prohibición de identificadores con prefijos reservados para el compilador (__ o _[A-Z])",
        "categoria": "Sintaxis Básica y Nomenclatura (0x00XX)",
        "archivo_apunte": "0_sintaxis.md",
        "descripcion": "El estándar C reserva todos los identificadores que comienzan con doble guión bajo o un guión bajo seguido de mayúscula para uso interno de la implementación y libc.",
        "ejemplo_correcto": "int valor_interno = 10;",
        "ejemplo_incorrecto": "int __valor = 10;\nint _Privado = 5;",
        "autofix": "No",
    },
    "0x0019h": {
        "codigo": "0x0019h",
        "alias": "GAFF_0x0019h",
        "titulo": "Prohibición de espacios en blanco antes de separadores de sintaxis (; y ,)",
        "categoria": "Sintaxis Básica y Nomenclatura (0x00XX)",
        "archivo_apunte": "0_sintaxis.md",
        "descripcion": "Los signos de puntuación ';' y ',' no deben estar precedidos por espacios en blanco. Deben situarse inmediatamente tras el operando anterior.",
        "ejemplo_correcto": "int a, b = 10;",
        "ejemplo_incorrecto": "int a , b = 10 ;",
        "autofix": "Sí",
    },
    "0x1010h": {
        "codigo": "0x1010h",
        "alias": "GAFF_0x1010h",
        "titulo": "Delimitación obligatoria con bloque de llaves en lazos do-while",
        "categoria": "Estructuras de Control y Lazos (0x10XX)",
        "archivo_apunte": "1_control.md",
        "descripcion": "Toda estructura 'do ... while' debe encerrar su cuerpo entre llaves explícitas '{ ... }' para evitar confusiones sintácticas con sentencias while independientes.",
        "ejemplo_correcto": "do {\n    x++;\n} while (x < 10);",
        "ejemplo_incorrecto": "do x++; while (x < 10);",
        "autofix": "No",
    },
    "0x1011h": {
        "codigo": "0x1011h",
        "alias": "GAFF_0x1011h",
        "titulo": "Prohibición de cláusula else redundante tras sentencia de retorno anticipado",
        "categoria": "Estructuras de Control y Lazos (0x10XX)",
        "archivo_apunte": "1_control.md",
        "descripcion": "Si una rama 'if' concluye incondicionalmente con 'return;', la cláusula 'else' posterior es redundante. Desanidá el flujo para mantener bajo el nivel de indentación.",
        "ejemplo_correcto": "if (error) {\n    return -1;\n}\nprocesar_exito();\nreturn 0;",
        "ejemplo_incorrecto": "if (error) {\n    return -1;\n} else {\n    procesar_exito();\n    return 0;\n}",
        "autofix": "No",
    },
    "0x2010h": {
        "codigo": "0x2010h",
        "alias": "GAFF_0x2010h",
        "titulo": "Prohibición de sombreado de parámetros mediante variables locales con el mismo nombre",
        "categoria": "Funciones y Modularización (0x20XX)",
        "archivo_apunte": "2_funciones.md",
        "descripcion": "Declarar una variable local con el mismo identificador que un parámetro de la función oculta (shadows) el argumento recibido y propicia errores de asignación engañosa.",
        "ejemplo_correcto": "void procesar(int cantidad) {\n    int factor = cantidad * 2;\n}",
        "ejemplo_incorrecto": "void procesar(int cantidad) {\n    int cantidad = 10; // shadowing de parametro\n}",
        "autofix": "No",
    },
    "0x2011h": {
        "codigo": "0x2011h",
        "alias": "GAFF_0x2011h",
        "titulo": "Prohibición de reasignar o modificar parámetros recibidos por valor dentro de la función",
        "categoria": "Funciones y Modularización (0x20XX)",
        "archivo_apunte": "2_funciones.md",
        "descripcion": "Modificar un parámetro primitivo recibido por valor (ej: n = 10; n++) confunde el contrato de entrada. Copiá el valor a una variable local explícita si requerís mutabilidad.",
        "ejemplo_correcto": "int calcular(int limite) {\n    int restante = limite;\n    while (restante > 0) restante--;\n    return restante;\n}",
        "ejemplo_incorrecto": "int calcular(int limite) {\n    while (limite > 0) limite--;\n    return limite;\n}",
        "autofix": "No",
    },
    "0x3018h": {
        "codigo": "0x3018h",
        "alias": "GAFF_0x3018h",
        "titulo": "Prohibición de invocar free() sobre punteros declarados con calificador const",
        "categoria": "Punteros y Gestión de Memoria (0x30XX)",
        "archivo_apunte": "3_punteros.md",
        "descripcion": "Pasar un puntero constante a free() (incluso con cast de descarte) indica que la memoria no es de propiedad modificable o proviene de segmentos estáticos/text de sólo lectura.",
        "ejemplo_correcto": "char *buffer = malloc(32);\nfree(buffer);\nbuffer = NULL;",
        "ejemplo_incorrecto": "const char *fijo = \"texto\";\nfree((void *)fijo);",
        "autofix": "No",
    },
    "0x3019h": {
        "codigo": "0x3019h",
        "alias": "GAFF_0x3019h",
        "titulo": "Prohibición de comparar punteros contra constantes numéricas distintas de NULL o cero",
        "categoria": "Punteros y Gestión de Memoria (0x30XX)",
        "archivo_apunte": "3_punteros.md",
        "descripcion": "Comparar un puntero contra enteros mayores a cero (ej: ptr == 1 o ptr > 0) es sintaxis inválida y de comportamiento no portable en C estándar.",
        "ejemplo_correcto": "if (ptr != NULL) { ... }",
        "ejemplo_incorrecto": "if (ptr == 1) { ... }\nif (ptr > 0) { ... }",
        "autofix": "No",
    },
    "0x400Ah": {
        "codigo": "0x400Ah",
        "alias": "GAFF_0x400Ah",
        "titulo": "Prohibición de operar sobre flujos de archivo tras haber invocado fclose() (use-after-close)",
        "categoria": "Gestión de Archivos y Errores (0x40XX)",
        "archivo_apunte": "4_archivos.md",
        "descripcion": "Utilizar un puntero a FILE* en funciones de E/S tras haber sido cerrado con fclose() provoca violaciones de segmento y corrupción del estado del runtime.",
        "ejemplo_correcto": "FILE *f = fopen(\"log.txt\", \"r\");\n...\nfclose(f);\nf = NULL;",
        "ejemplo_incorrecto": "FILE *f = fopen(\"log.txt\", \"r\");\nfclose(f);\nfread(buf, 1, 10, f); // use-after-close",
        "autofix": "No",
    },
    "0x500Eh": {
        "codigo": "0x500Eh",
        "alias": "GAFF_0x500Eh",
        "titulo": "Prohibición de la biblioteca obsoleta y no estándar <conio.h> (getch, clrscr)",
        "categoria": "Compilación y Buenas Prácticas de Ingeniería (0x50XX)",
        "archivo_apunte": "5_buenas_practicas.md",
        "descripcion": "La biblioteca <conio.h> no pertenece a ANSI/ISO C ni al estándar POSIX. Funciones como getch() o clrscr() impiden la compilación en sistemas Linux y GCC moderno.",
        "ejemplo_correcto": "#include <stdio.h>\nint c = getchar();\nprintf(\"\\033[2J\");",
        "ejemplo_incorrecto": "#include <conio.h>\nint c = getch();\nclrscr();",
        "autofix": "No",
    },
}

# Alias bidireccionales para retrocompatibilidad
def cargar_reglas_desde_apunte(directorio_apunte: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    """Carga y sincroniza las reglas canónicas directamente desde p1-apunte/reglas."""
    rutas_candidatas = [
        Path(os.environ.get("P1_REGLAS_DIR", "")) if os.environ.get("P1_REGLAS_DIR") else None,
        directorio_apunte,
        Path("/home/mrtin/dev/edu-sitios/p1-apunte/reglas"),
        Path.cwd().parents[1] / "edu-sitios" / "p1-apunte" / "reglas",
        Path(__file__).resolve().parents[5] / "edu-sitios" / "p1-apunte" / "reglas",
    ]
    dir_valido: Optional[Path] = None
    for r in rutas_candidatas:
        if r and r.is_dir():
            dir_valido = r
            break

    if not dir_valido:
        return CATALOGO_REGLAS

    CATEGORIAS = {
        "0_sintaxis.md": "Sintaxis Básica y Nomenclatura (0x00XX)",
        "1_control.md": "Estructuras de Control y Lazos (0x10XX)",
        "2_funciones.md": "Funciones y Modularización (0x20XX)",
        "3_punteros.md": "Punteros y Gestión de Memoria (0x30XX)",
        "4_archivos.md": "Gestión de Archivos y Errores (0x40XX)",
        "5_buenas_practicas.md": "Compilación y Buenas Prácticas de Ingeniería (0x50XX)",
    }

    pattern = r"(?:(?:\([0-9a-fA-FxX]+h?\)\s*=\s*)?##\s*Regla\s*`?(0x[0-9a-fA-F]+h)`?\s*(?::|\n\s*:)\s*)"

    for fname, cat in CATEGORIAS.items():
        fpath = dir_valido / fname
        if not fpath.is_file():
            continue
        try:
            content = fpath.read_text(encoding="utf-8")
        except Exception:
            continue

        parts = re.split(pattern, content)
        for i in range(1, len(parts), 2):
            code = parts[i].strip()
            body = parts[i + 1]
            lines = body.strip().splitlines()
            title = lines[0].strip().rstrip(":").replace("`", "")

            desc_parts = []
            for p in re.split(r"\n\s*\n", "\n".join(lines[1:])):
                p_s = p.strip()
                if p_s.startswith("```") or p_s.startswith("- ") or p_s.startswith("###") or p_s.startswith("<!--"):
                    break
                desc_parts.append(p_s)
            desc = " ".join(desc_parts).replace("\n", " ").strip()

            ejemplo_inc = ""
            ejemplo_corr = ""
            diff_m = re.search(r"```\s*diff\s*\n(.*?)\n```", body, re.DOTALL)
            if diff_m:
                d_lines = diff_m.group(1).splitlines()
                ejemplo_inc = "\n".join(l[1:].strip() for l in d_lines if l.startswith("-"))
                ejemplo_corr = "\n".join(l[1:].strip() for l in d_lines if l.startswith("+"))
            else:
                inc_m = re.search(r"(?:-|\*\*)\s*(?:Identificadores\s+inadecuados?|Inadecuados?|Incorrecto[^:]*):\s*\n+```[a-zA-Z]*\s*\n(.*?)\n```", body, re.DOTALL | re.IGNORECASE)
                corr_m = re.search(r"(?:-|\*\*)\s*(?:Identificadores\s+adecuados?|Adecuados?|Correcto[^:]*):\s*\n+```[a-zA-Z]*\s*\n(.*?)\n```", body, re.DOTALL | re.IGNORECASE)
                if inc_m:
                    ejemplo_inc = inc_m.group(1).strip()
                if corr_m:
                    ejemplo_corr = corr_m.group(1).strip()

            if code in CATALOGO_REGLAS:
                CATALOGO_REGLAS[code]["titulo"] = title
                CATALOGO_REGLAS[code]["categoria"] = cat
                CATALOGO_REGLAS[code]["archivo_apunte"] = fname
                if desc:
                    CATALOGO_REGLAS[code]["descripcion"] = desc
                if ejemplo_corr:
                    CATALOGO_REGLAS[code]["ejemplo_correcto"] = ejemplo_corr
                if ejemplo_inc:
                    CATALOGO_REGLAS[code]["ejemplo_incorrecto"] = ejemplo_inc
            else:
                CATALOGO_REGLAS[code] = {
                    "codigo": code,
                    "alias": f"GAFF_{code}",
                    "titulo": title,
                    "categoria": cat,
                    "archivo_apunte": fname,
                    "descripcion": desc,
                    "ejemplo_correcto": ejemplo_corr or "// Código conforme a cátedra",
                    "ejemplo_incorrecto": ejemplo_inc or "// Código no conforme",
                    "autofix": "Sí" if code in ("0x0004h", "0x0005h", "0x0006h", "0x000Bh", "0x5003h") else "No",
                }

    return CATALOGO_REGLAS


def obtener_regla(codigo: str) -> Optional[Dict[str, Any]]:
    """Busca una regla por código hex de cátedra (0xXXXXh, 0xXXXX) de forma insensible a mayúsculas."""
    cod = codigo.strip().lower()
    cod_h = cod + "h" if (cod.startswith("0x") and not cod.endswith("h")) else cod

    for k, info in CATALOGO_REGLAS.items():
        k_low = k.lower()
        if k_low in (cod, cod_h):
            return info
        if info.get("codigo", "").lower() in (cod, cod_h):
            return info

    return None




# Carga y sincronización inicial con p1-apunte/reglas
cargar_reglas_desde_apunte()
