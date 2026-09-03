/*
 * REGLA 0x3006h: Documentá la propiedad de los recursos al utilizar punteros
 *
 * Categoria: Punteros y Gestión de Memoria (0x30XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Cuando una función recibe o devuelve un puntero a memoria dinámica, la documentación de la función debe especificar explícitamente cuál es el módulo responsable de liberar dicha memoria (el dueño del recurso).
 *
 * Ejemplo canónico correcto según cátedra:
 * /** @return Puntero asignado. El llamador debe liberar con free(). */
 */

/**
 * Crea un elemento.
 */
int *elemento_crear(void)
{
    int *p = malloc(sizeof(int));
    if (p == NULL) return NULL;
    return p;
}
