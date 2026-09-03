/*
 * REGLA 0x5002h: Desarrollá y compilá siempre con todas las advertencias del compilador activadas
 *
 * Categoria: Compilación y Buenas Prácticas de Ingeniería (0x50XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Debés activar las advertencias de compilación para la detección temprana de errores lógicos. Usá al menos las siguientes banderas con `gcc` o `clang`:
 *
 * Ejemplo canónico correcto según cátedra:
 * CFLAGS = -Wall -Wextra -Werror -pedantic -std=c11
 */

#pragma GCC diagnostic ignored "-Wunused-variable"
int main(void)
{
    return 0;
}
