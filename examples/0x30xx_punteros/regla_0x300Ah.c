/*
 * REGLA 0x300Ah: Utilizá cast explícito al convertir tipos de punteros
 *
 * Categoria: Punteros y Gestión de Memoria (0x30XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Las conversiones de tipos de punteros deben ser siempre explícitas en el código fuente para mejorar la claridad de conversión de tipos de datos.
 *
 * Ejemplo canónico correcto según cátedra:
 * int *ptr = (int *)mem;
 */

void test_violacion(void)
{
    int *ptr = mem;
}
