/*
 * REGLA 0x1001h: Todas las estructuras de control deben utilizar llaves
 *
 * Categoria: Estructuras de Control y Lazos (0x10XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Aunque las llaves son opcionales para bloques de una sola línea, su uso es obligatorio para mantener la prolijidad y consistencia, y para evitar que futuras modificaciones introduzcan comportamientos inesperados.
 *
 * Ejemplo canónico correcto según cátedra:
 * if (x > 0)
 * {
 *     x++;
 * }
 */

void test_violacion(void)
{
    if (x > 0)
    x++;
}
