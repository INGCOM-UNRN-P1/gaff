/*
 * REGLA 0x0019h: Prohibición de espacios en blanco antes de separadores de sintaxis (; y ,)
 *
 * Categoria: Sintaxis Básica y Nomenclatura (0x00XX)
 * Autofix disponible: Sí
 *
 * Descripcion:
 * Los signos de puntuación ';' y ',' no deben estar precedidos por espacios en blanco. Deben situarse inmediatamente tras el operando anterior.
 *
 * Ejemplo canónico correcto según cátedra:
 * int a, b = 10;
 */

void test(void)
{
    int a , b = 10 ;
    (void)a;
    (void)b;
}
