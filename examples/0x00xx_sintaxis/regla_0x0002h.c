/*
 * REGLA 0x0002h: Una declaración de variable por línea
 *
 * Categoria: Sintaxis Básica y Nomenclatura (0x00XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Declarar cada variable en una línea separada para facilitar comentarios y legibilidad.
 *
 * Ejemplo canónico correcto según cátedra:
 * int a;
 * int b;
 * int c;
 */

void test_violacion(void)
{
    int a, b, c;
}
