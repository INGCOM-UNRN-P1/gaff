/*
 * REGLA 0x5004h: Todas las operaciones con cadenas deben ser seguras
 *
 * Categoria: Compilación y Buenas Prácticas de Ingeniería (0x50XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Utilizá funciones que controlen los límites de tamaño máximo del buffer de destino (`strncpy`, `snprintf`, `strncat`) para prevenir desbordamientos.
 *
 * Ejemplo canónico correcto según cátedra:
 * snprintf(dest, sizeof(dest), "%s", orig);
 */

void test_violacion(void)
{
    strcpy(dest, orig);
strcat(dest, extra);
}
