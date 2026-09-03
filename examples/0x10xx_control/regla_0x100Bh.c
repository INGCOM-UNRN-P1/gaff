/*
 * REGLA 0x100Bh: Prohibición de estructuras de control con cuerpo vacío (if (...);)
 *
 * Categoria: Estructuras de Control y Lazos (0x10XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Un punto y coma inmediatamente tras el paréntesis de un if o while crea un bloque nulo y casi siempre representa un error lógico grave.
 *
 * Ejemplo canónico correcto según cátedra:
 * if (x > 0) {
 *     procesar(x);
 * }
 */

void test_violacion(void)
{
    if (x > 0);
{
    procesar(x);
}
}
