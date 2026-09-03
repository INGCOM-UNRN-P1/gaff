/*
 * REGLA 0x0001h: Los identificadores deben ser descriptivos
 *
 * Categoria: Sintaxis Básica y Nomenclatura (0x00XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Los nombres de variables, funciones y demás identificadores deben reflejar con precisión su propósito. Esto contribuye a que el código sea autodescriptivo, minimizando la necesidad de comentarios adicionales. El uso de nombres significativos facilita la lectura y la comprensión.
 *
 * Ejemplo canónico correcto según cátedra:
 * int precio_total = obtener_precio();
 */

void test_violacion(void)
{
    int a = obtener_precio();
}
