/*
 * REGLA 0x001Bh: Prohibición de espacios en blanco entre operadores unarios (++, --, !) y su operando
 *
 * Categoria: Sintaxis Básica y Nomenclatura (0x00XX)
 * Autofix disponible: Sí
 *
 * Descripcion:
 * Los operadores unarios de incremento, decremento y negación lógica deben estar adheridos a su operando sin separación de espacios en blanco.
 *
 * Ejemplo canónico correcto según cátedra:
 * i++;
 * ++j;
 * if (!activo) { ... }
 */

void test(int x)
{
    x ++;
    (void)x;
}
