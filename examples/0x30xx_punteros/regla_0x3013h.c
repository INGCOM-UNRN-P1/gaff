/*
 * REGLA 0x3013h: Asignación de memoria con sizeof sobre puntero en lugar del tipo apuntado
 *
 * Categoria: Punteros y Gestión de Memoria (0x30XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Al alocar memoria dinámica con 'ptr = malloc(...)', debe usarse 'sizeof(*ptr)' o 'sizeof(tipo)'. Usar 'sizeof(ptr)' reserva solo el tamaño del puntero (4 u 8 bytes) provocando desbordamientos.
 *
 * Ejemplo canónico correcto según cátedra:
 * int *arr = malloc(10 * sizeof(*arr));
 */

void test_violacion(void)
{
    int *arr = malloc(10 * sizeof(arr));
}
