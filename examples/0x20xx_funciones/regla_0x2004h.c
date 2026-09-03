/*
 * REGLA 0x2004h: No se permite el uso de variables globales
 *
 * Categoria: Funciones y Modularización (0x20XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Las variables globales pueden ser modificadas desde cualquier parte del programa, lo que causa efectos secundarios impredecibles y dificulta el rastreo de errores. **Su uso está estrictamente prohibido**.
 *
 * Ejemplo canónico correcto según cátedra:
 * const double PI = 3.14159265;
 * #define BUFFER_MAX 1024
 */

int variable_global_insegura = 10;
int main(void) { return 0; }
