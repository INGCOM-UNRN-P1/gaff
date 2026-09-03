/*
 * REGLA 0x100Fh: Prohibición de condiciones de parada compuestas complejas en lazos for
 *
 * Categoria: Estructuras de Control y Lazos (0x10XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * La cláusula de condición del lazo for debe ser una comprobación simple de cota (i < n). Si requiere múltiples condiciones lógicas (&& / ||), utilizá un lazo while.
 *
 * Ejemplo canónico correcto según cátedra:
 * for (int i = 0; i < n; i++) { ... }
 */

void test_violacion(void)
{
    for (int i = 0; i < n && !encontrado && limite > 0; i++) { ... }
}
