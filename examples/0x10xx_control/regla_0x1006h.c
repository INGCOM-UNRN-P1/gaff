/*
 * REGLA 0x1006h: No utilizar la instrucción goto
 *
 * Categoria: Estructuras de Control y Lazos (0x10XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * El uso de `goto` rompe el flujo de control estructurado, dificultando la lectura y depuración del código. En su lugar, empleá las estructuras de control estándar.
 *
 * Ejemplo canónico correcto según cátedra:
 * Utilizar estructuras de bucle y retornos limpios estructurados.
 */

void test_violacion(void)
{
    goto cleanup;
}
