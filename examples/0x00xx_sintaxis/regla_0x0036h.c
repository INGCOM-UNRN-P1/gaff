/*
 * REGLA 0x0036h: Asigná NULL al puntero tras liberar un recurso opaco en el ámbito del cliente
 *
 * Categoria: Punteros y Gestión de Memoria (0x30XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Al destruir o liberar una instancia de un tipo opaco mediante su función destructora, es mandatorio asignar `NULL` al puntero correspondiente en el código del cliente para evitar el uso accidental de punteros colgantes o referencias inválidas.
 *
 * Ejemplo canónico correcto según cátedra:
 * lista_destruir(mi_lista);
 * mi_lista = NULL;
 */

void test_violacion(void)
{
    lista_destruir(mi_lista);
}
