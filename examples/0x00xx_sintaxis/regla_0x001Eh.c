/*
 * REGLA 0x001Eh: Prohibición de múltiples espacios en blanco consecutivos dentro de una línea de código
 *
 * Categoria: Sintaxis Básica y Nomenclatura (0x00XX)
 * Autofix disponible: Sí
 *
 * Descripcion:
 * Salvo la sangría inicial que delimita los bloques, no deben colocarse dos o más espacios consecutivos entre identificadores, operadores o palabras clave.
 *
 * Ejemplo canónico correcto según cátedra:
 * int total = cantidad * precio;
 */

void test(void)
{
    int   total   =   10;
    (void)total;
}
