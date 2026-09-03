/*
 * REGLA 0x2007h: Mantené el alcance de las variables al mínimo posible
 *
 * Categoria: Funciones y Modularización (0x20XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Declarar las variables con el alcance más restringido posible ayuda a reducir errores y mejora la claridad de la vida útil de cada dato.
 *
 * Ejemplo canónico correcto según cátedra:
 * for (int i = 0; i < n; i++) { ... }
 */

void f(void)
{
    int i;
    for (i = 0; i < 10; i++)
    {
        printf("%d", i);
    }
}
