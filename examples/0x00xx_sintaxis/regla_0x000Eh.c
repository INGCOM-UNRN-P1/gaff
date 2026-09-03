/*
 * REGLA 0x000Eh: Los nombres de funciones deben usar snake_case estricto en minúsculas
 *
 * Categoria: 0x00xx_sintaxis
 * Autofix disponible: No
 *
 * Descripcion:
 * Todas las funciones deben nombrarse en snake_case en minúsculas, sin mezclar camelCase ni PascalCase.
 *
 * Ejemplo canónico correcto según cátedra:
 * int procesar_vector(int *vec, size_t n);
 */

int calcularPromedio(int a, int b)
{
    return (a + b) / 2;
}
