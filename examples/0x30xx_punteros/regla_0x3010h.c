/*
 * REGLA 0x3010h: Las variables que representan tamaños o índices de arreglos deben ser de tipo size_t
 *
 * Categoria: Punteros y Gestión de Memoria (0x30XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * `size_t` es un tipo entero sin signo que garantiza portabilidad para contener el tamaño máximo posible de un objeto en memoria.
 *
 * Ejemplo canónico correcto según cátedra:
 * size_t longitud = strlen(cadena);
 */

void test_violacion(void)
{
    int longitud = strlen(cadena);
}
