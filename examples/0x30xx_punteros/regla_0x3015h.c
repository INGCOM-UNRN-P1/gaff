/*
 * REGLA 0x3015h: Reallocación segura: no sobreescribir el puntero original directamente
 *
 * Categoria: Punteros y Gestión de Memoria (0x30XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Asignar 'p = realloc(p, size)' causa fuga de memoria si realloc() falla y retorna NULL. Utilizar siempre una variable temporal.
 *
 * Ejemplo canónico correcto según cátedra:
 * int *tmp = realloc(p, nuevo_tam);
 * if (tmp != NULL) p = tmp;
 */

void test_violacion(void)
{
    p = realloc(p, nuevo_tam);
}
