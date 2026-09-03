/*
 * REGLA 0x0006h: El asterisco de los punteros debe declararse junto al identificador
 *
 * Categoria: Sintaxis Básica y Nomenclatura (0x00XX)
 * Autofix disponible: Sí
 *
 * Descripcion:
 * Esta convención facilita la identificación visual de una variable como puntero y mejora la claridad.
 *
 * Ejemplo canónico correcto según cátedra:
 * int *ptr;
 */

void test_violacion(void)
{
    int* ptr;
}
