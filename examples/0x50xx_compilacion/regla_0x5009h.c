/*
 * REGLA 0x5009h: Prohibición de división entera no intencional asignada a flotantes
 *
 * Categoria: Compilación y Buenas Prácticas de Ingeniería (0x50XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Asignar el resultado de una división entre enteros a un float o double (ej: double d = 1 / 2) trunca a cero antes de la asignación. Usar literales flotantes (1.0 / 2).
 *
 * Ejemplo canónico correcto según cátedra:
 * double tasa = 1.0 / 2.0;
 */

void test_violacion(void)
{
    double tasa = 1 / 2;
}
