/*
 * REGLA 0x3001h: Siempre verificá la asignación exitosa de memoria dinámica
 *
 * Categoria: Punteros y Gestión de Memoria (0x30XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Toda asignación de memoria dinámica realizada con `malloc`, `calloc` o `realloc` debe ser seguida inmediatamente por una comprobación contra `NULL` antes de su uso.
 *
 * Ejemplo canónico correcto según cátedra:
 * ptr = malloc(sizeof(*ptr));
 * if (ptr == NULL) {
 *     return NULL;
 * }
 */

void test_violacion(void)
{
    ptr = malloc(sizeof(*ptr));
ptr->dato = 10; // Falla si no hay memoria
}
