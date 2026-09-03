/*
 * REGLA 0x1008h: Toda instrucción switch debe incluir un caso default
 *
 * Categoria: Estructuras de Control y Lazos (0x10XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Para garantizar un comportamiento predecible y robusto, toda instrucción `switch` debe finalizar con un bloque `default`. Esto asegura que el programa maneje explícitamente cualquier valor inesperado. Si un `case` intencionalmente no contiene una instrucción `break` para "caer" (`fall-through`) al siguiente caso, esta intención debe ser documentada con un comentario.
 *
 * Ejemplo canónico correcto según cátedra:
 * switch (cmd) {
 *     case 1: ... break;
 *     default: ... break;
 * }
 */

void test_violacion(void)
{
    switch (cmd) {
    case 1: ... break;
}
}
