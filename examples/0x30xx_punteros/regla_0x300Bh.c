/*
 * REGLA 0x300Bh: Usá siempre sizeof en las asignaciones de memoria dinámica, prefiriendo sizeof(*ptr)
 *
 * Categoria: Punteros y Gestión de Memoria (0x30XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * El uso de `sizeof` dinámico en asignación reduce errores ante cambios de tipos en refactorizaciones de variables.
 *
 * Ejemplo canónico correcto según cátedra:
 * ptr = malloc(sizeof(*ptr));
 */

void test_violacion(void)
{
    ptr = malloc(4);
}
