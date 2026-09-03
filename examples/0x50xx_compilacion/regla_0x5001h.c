/*
 * REGLA 0x5001h: Los arreglos estáticos deben ser creados con un tamaño fijo en tiempo de compilación
 *
 * Categoria: Compilación y Buenas Prácticas de Ingeniería (0x50XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Los Arreglos de Longitud Variable (ALV / VLA) están prohibidos debido a los riesgos de desbordamiento incontrolado de la pila. Deben definirse con una constante en tiempo de compilación.
 *
 * Ejemplo canónico correcto según cátedra:
 * #define TAMANO_NUMEROS 10
 * int numeros[TAMANO_NUMEROS];
 */

void test_violacion(void)
{
    int n = 10;
int numeros[n]; // ALV prohibido
}
