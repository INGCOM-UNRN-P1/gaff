/*
 * REGLA 0x0016h: Prohibición de identificadores que colisionen con palabras clave o tipos estándar
 *
 * Categoria: Sintaxis Básica y Nomenclatura (0x00XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * No utilizar palabras reservadas o tipos estándar de C99/C11/POSIX (restrict, inline, bool, true, false, nullptr, alignas) como nombres de variables o parámetros.
 *
 * Ejemplo canónico correcto según cátedra:
 * bool es_valido = true;
 * int limite = 10;
 */

void test_violacion(void)
{
    int bool = 1;
int restrict = 0;
}
