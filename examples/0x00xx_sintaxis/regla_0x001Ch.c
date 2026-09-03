/*
 * REGLA 0x001Ch: Espacio en blanco obligatorio tras la coma separadora en listas y argumentos
 *
 * Categoria: Sintaxis Básica y Nomenclatura (0x00XX)
 * Autofix disponible: Sí
 *
 * Descripcion:
 * Toda coma ',' utilizada para separar argumentos de función, parámetros o declaraciones múltiples debe estar seguida por exactamente un espacio en blanco.
 *
 * Ejemplo canónico correcto según cátedra:
 * int a, b = 0;
 * foo(x, y, z);
 */

void f(int a, int b) { (void)a; (void)b; }
void test(void)
{
    f(1,2);
}
