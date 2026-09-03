/*
 * REGLA 0x100Eh: Prohibición de condiciones constantes o tautológicas en sentencias if
 *
 * Categoria: Estructuras de Control y Lazos (0x10XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * No utilizar literales booleanos o enteros constantes (1, 0, true, false) como condición en sentencias if; denota código de depuración residual o ramificación muerta.
 *
 * Ejemplo canónico correcto según cátedra:
 * if (activo) { ... }
 */

void test_violacion(void)
{
    if (1) { ... }
if (false) { ... }
}
