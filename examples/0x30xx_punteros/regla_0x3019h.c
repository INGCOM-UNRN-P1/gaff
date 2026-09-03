/*
 * REGLA 0x3019h: Prohibición de comparar punteros contra constantes numéricas distintas de NULL o cero
 *
 * Categoria: Punteros y Gestión de Memoria (0x30XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Comparar un puntero contra enteros mayores a cero (ej: ptr == 1 o ptr > 0) es sintaxis inválida y de comportamiento no portable en C estándar.
 *
 * Ejemplo canónico correcto según cátedra:
 * if (ptr != NULL) { ... }
 */

void test_ptr(int *ptr)
{
    if (ptr == 1) {
        return;
    }
}
