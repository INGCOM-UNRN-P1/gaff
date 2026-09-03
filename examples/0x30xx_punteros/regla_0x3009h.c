/*
 * REGLA 0x3009h: Documentá explícitamente los casos en que una función puede retornar NULL
 *
 * Categoria: Punteros y Gestión de Memoria (0x30XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Si una función que devuelve un puntero puede fallar y retornar `NULL`, este escenario debe ser explícito en la documentación de retorno de la función.
 *
 * Ejemplo canónico correcto según cátedra:
 * /** @return Puntero al elemento, o NULL si no existe. */
 */

/**
 * Busca el registro.
 * @return El registro encontrado.
 */
int *buscar_registro(int id)
{
    if (id < 0) return NULL;
    return NULL;
}
