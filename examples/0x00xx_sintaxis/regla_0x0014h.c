/*
 * REGLA 0x0014h: Prohibición de identificadores con caracteres no ASCII (acentos, ñ)
 *
 * Categoria: Sintaxis Básica y Nomenclatura (0x00XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Los nombres de variables, funciones y tipos deben restringirse al conjunto ASCII estándar [a-zA-Z0-9_]. El uso de tildes o 'ñ' compromete la portabilidad entre compiladores y sistemas operativos.
 *
 * Ejemplo canónico correcto según cátedra:
 * int anio = 2026;
 * float numero = 3.14;
 */

void test_violacion(void)
{
    int año = 2026;
float número = 3.14;
}
