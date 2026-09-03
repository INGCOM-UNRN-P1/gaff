/*
 * REGLA 0x0037h: Evitá identificadores genéricos con sufijo numérico (numero1, num_1, etc.)
 *
 * Categoria: 0x00xx_sintaxis
 * Autofix disponible: No
 *
 * Descripcion:
 * Los identificadores genéricos seguidos de un número (como 'numero1', 'numero_1', 'num1', 'var1', 'dato1', etc.) denotan una elección pobre de nombres y falta de abstracción. Usá nombres que reflejen el rol semántico específico o utilizá un arreglo si representan una colección.
 *
 * Ejemplo canónico correcto según cátedra:
 * int dividendo = 10, divisor = 2;
 * int valores[2] = {10, 2};
 */

void test_violacion(void)
{
    int numero1 = 10, numero2 = 2;
int num_1 = 10, num_2 = 2;
}
