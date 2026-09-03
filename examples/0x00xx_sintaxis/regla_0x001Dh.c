/*
 * REGLA 0x001Dh: Prohibición de espacios en blanco internos inmediatamente tras '(' o antes de ')'
 *
 * Categoria: Sintaxis Básica y Nomenclatura (0x00XX)
 * Autofix disponible: Sí
 *
 * Descripcion:
 * No deben dejarse espacios en blanco inmediatamente tras el paréntesis de apertura ni antes del paréntesis de cierre en expresiones, condiciones o invocaciones.
 *
 * Ejemplo canónico correcto según cátedra:
 * if (x > 0) {
 *     foo(a, b);
 * }
 */

void test(int x)
{
    if ( x > 0 ) {
        return;
    }
}
