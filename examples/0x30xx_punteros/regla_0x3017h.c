/*
 * REGLA 0x3017h: Prohibición de utilizar free() como valor o dentro de expresiones compuestas
 *
 * Categoria: Punteros y Gestión de Memoria (0x30XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * La función free() retorna void y tiene como único propósito la liberación de memoria. No debe asignarse a variables ni formar parte de operaciones aritméticas o condicionales.
 *
 * Ejemplo canónico correcto según cátedra:
 * free(ptr);
 * ptr = NULL;
 */

void test_violacion(void)
{
    int res = (free(ptr), 0);
}
