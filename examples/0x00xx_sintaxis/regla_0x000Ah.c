/*
 * REGLA 0x000Ah: Escribí comentarios que expliquen el "porqué", no el "qué"
 *
 * Categoria: Sintaxis Básica y Nomenclatura (0x00XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Los comentarios deben aportar valor y aclarar la intención detrás del código, no parafrasear lo que el código ya expresa de forma evidente. El código en sí mismo debe ser lo suficientemente claro para explicar *qué* hace.
 *
 * Ejemplo canónico correcto según cátedra:
 * // Usamos índice inverso porque el último byte define la paridad del paquete
 * for (size_t i = len - 1; i < len; i--)
 */

void test_violacion(void)
{
    // Incrementa i en 1
i++;
}
