/*
 * REGLA 0x300Dh: Utilizá enum en lugar de "números mágicos" para conjuntos de estados y valores constantes
 *
 * Categoria: Punteros y Gestión de Memoria (0x30XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Las enumeraciones explican la semántica de un conjunto de constantes enteras relacionadas.
 *
 * Ejemplo canónico correcto según cátedra:
 * #define MAX_INTENTOS 5
 * for (int i = 0; i < MAX_INTENTOS; i++)
 */

void test_violacion(void)
{
    for (int i = 0; i < 5; i++) // ¿Qué significa 5?
}
