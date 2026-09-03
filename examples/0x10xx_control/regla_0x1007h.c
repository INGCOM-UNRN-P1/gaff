/*
 * REGLA 0x1007h: No utilizar el operador condicional (ternario) ?:
 *
 * Categoria: Estructuras de Control y Lazos (0x10XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Aunque compacto, el operador ternario reduce la legibilidad del código, especialmente en expresiones anidadas o complejas.
 *
 * Ejemplo canónico correcto según cátedra:
 * if (a > b) {
 *     res = a;
 * } else {
 *     res = b;
 * }
 */

void test_violacion(void)
{
    res = (a > b) ? a : b;
}
