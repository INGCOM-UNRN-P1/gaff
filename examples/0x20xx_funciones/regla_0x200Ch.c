/*
 * REGLA 0x200Ch: Prohibición de retornar la dirección de una variable local de stack
 *
 * Categoria: Funciones y Modularización (0x20XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Retornar un puntero a una variable local de stack (&variable) genera un puntero colgante (dangling pointer) ya que el marco de activación se destruye al finalizar la función.
 *
 * Ejemplo canónico correcto según cátedra:
 * int *crear(void) {
 *     int *p = malloc(sizeof(int));
 *     return p;
 * }
 */

void test_violacion(void)
{
    int *crear(void) {
    int x = 10;
    return &x;
}
}
