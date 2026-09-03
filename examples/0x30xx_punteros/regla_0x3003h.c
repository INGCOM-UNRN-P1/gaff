/*
 * REGLA 0x3003h: No mezcles operaciones de asignación y comparación en una sola línea
 *
 * Categoria: Punteros y Gestión de Memoria (0x30XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Mantener las asignaciones y comparaciones en líneas separadas previene errores lógicos sutiles y facilita el rastreo de excepciones.
 *
 * Ejemplo canónico correcto según cátedra:
 * ptr = malloc(tamaño);
 * if (ptr == NULL)
 * {
 */

void test_violacion(void)
{
    if ((ptr = malloc(tamaño)) == NULL)
{
}
