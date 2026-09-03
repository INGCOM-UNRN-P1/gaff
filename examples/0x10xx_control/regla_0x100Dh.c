/*
 * REGLA 0x100Dh: Prohibición de modificar la variable de control dentro del cuerpo del for
 *
 * Categoria: Estructuras de Control y Lazos (0x10XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * La variable de control de un lazo 'for' debe evolucionar exclusivamente en la cláusula de incremento. Modificarla en el cuerpo ofusca la condición de parada; preferí 'while'.
 *
 * Ejemplo canónico correcto según cátedra:
 * for (int i = 0; i < n; i++) {
 *     printf("%d", i);
 * }
 */

void test_violacion(void)
{
    for (int i = 0; i < n; i++) {
    if (cond) i += 2;
}
}
