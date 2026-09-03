/*
 * REGLA 0x0015h: Prohibición del operador coma para encadenar sentencias independientes
 *
 * Categoria: Sintaxis Básica y Nomenclatura (0x00XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * No encadenar asignaciones o sentencias mediante el operador coma (ej: x = 1, y = 2;). Cada sentencia debe residir en una línea independiente finalizada en punto y coma.
 *
 * Ejemplo canónico correcto según cátedra:
 * x = 1;
 * y = 2;
 */

void test_violacion(void)
{
    x = 1, y = 2;
}
