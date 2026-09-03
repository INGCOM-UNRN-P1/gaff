/*
 * REGLA 0x000Dh: No dejes código comentado (dead code) en los archivos fuente
 *
 * Categoria: 0x00xx_sintaxis
 * Autofix disponible: No
 *
 * Descripcion:
 * El código comentado ensucia el archivo y confunde al lector: debe eliminarse. El historial de cambios pertenece al control de versiones, no a los fuentes.
 *
 * Ejemplo canónico correcto según cátedra:
 * int total = calcular_total(precio);
 */

void test_violacion(void)
{
    // int total = calcular_total_viejo(precio);
int total = calcular_total(precio);
}
