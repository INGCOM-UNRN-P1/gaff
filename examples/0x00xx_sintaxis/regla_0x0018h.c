/*
 * REGLA 0x0018h: Prohibición de identificadores con prefijos reservados para el compilador (__ o _[A-Z])
 *
 * Categoria: Sintaxis Básica y Nomenclatura (0x00XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * El estándar C reserva todos los identificadores que comienzan con doble guión bajo o un guión bajo seguido de mayúscula para uso interno de la implementación y libc.
 *
 * Ejemplo canónico correcto según cátedra:
 * int valor_interno = 10;
 */

void test(void)
{
    int __valor_reservado = 10;
    (void)__valor_reservado;
}
