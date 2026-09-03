/*
 * REGLA 0x100Ah: Prohibición de asignaciones simples dentro de condiciones lógicas
 *
 * Categoria: Estructuras de Control y Lazos (0x10XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * No realizar asignaciones con '=' dentro de expresiones de control if o while. Usar '==' para comparar o evaluar la asignación en una línea previa.
 *
 * Ejemplo canónico correcto según cátedra:
 * if (estado == ACTIVO) { ... }
 */

void test_violacion(void)
{
    if (estado = ACTIVO) { ... }
}
