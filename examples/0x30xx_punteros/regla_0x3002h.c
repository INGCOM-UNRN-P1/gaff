/*
 * REGLA 0x3002h: Liberá siempre la memoria dinámica y asigná NULL al puntero para evitar punteros colgantes
 *
 * Categoria: Punteros y Gestión de Memoria (0x30XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Por cada asignación de memoria dinámica debe existir una correspondiente liberación con `free()`. Inmediatamente después de liberar la memoria, asigná `NULL` al puntero para prevenir fallos por acceso a punteros colgantes (*dangling pointers*).
 *
 * Ejemplo canónico correcto según cátedra:
 * free(ptr);
 * ptr = NULL;
 */

void test_violacion(void)
{
    free(ptr);
// ptr sigue apuntando a memoria liberada
}
