/*
 * REGLA 0x3014h: Prohibición de doble liberación de memoria (double free) sobre el mismo puntero
 *
 * Categoria: Punteros y Gestión de Memoria (0x30XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Invocar 'free(ptr)' dos veces consecutivas sobre el mismo puntero corrompe el heap del asignador de memoria (glibc / jemalloc) y provoca abortos inmediatos (SIGABRT).
 *
 * Ejemplo canónico correcto según cátedra:
 * free(ptr);
 * ptr = NULL;
 */

void test_violacion(void)
{
    free(ptr);
free(ptr);
}
