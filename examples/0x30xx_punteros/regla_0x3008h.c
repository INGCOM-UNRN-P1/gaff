/*
 * REGLA 0x3008h: Los punteros nulos deben ser inicializados y comparados con NULL, no con 0
 *
 * Categoria: Punteros y Gestión de Memoria (0x30XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * La macro `NULL` debe utilizarse para mantener la coherencia semántica en operaciones con punteros.
 *
 * Ejemplo canónico correcto según cátedra:
 * int *ptr = NULL;
 * if (ptr == NULL) { ... }
 */

void test_violacion(void)
{
    int *ptr = 0;
if (ptr == 0) { ... }
}
