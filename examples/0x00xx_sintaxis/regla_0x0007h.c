/*
 * REGLA 0x0007h: Los argumentos de función y las variables locales deben usar snake_case en minúsculas
 *
 * Categoria: Sintaxis Básica y Nomenclatura (0x00XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Todos los identificadores de variables y argumentos deben estar escritos en snake_case en minúsculas, evitando camelCase o PascalCase.
 *
 * Ejemplo canónico correcto según cátedra:
 * int calcular_promedio(int *vector_numeros, size_t longitud_total);
 */

int calcularPromedio(int *vectorNumeros, size_t LongitudTotal);
