/*
 * REGLA 0x0017h: Prohibición de notación húngara o prefijos redundantes de tipo en identificadores
 *
 * Categoria: Sintaxis Básica y Nomenclatura (0x00XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Evitar prefijos redundantes como 'int_', 'float_', 'str_', 'arr_' o notación húngara en nombres de variables. El tipo ya está determinado por el lenguaje.
 *
 * Ejemplo canónico correcto según cátedra:
 * int edad = 20;
 * char *nombre = "Ana";
 */

void test_violacion(void)
{
    int int_edad = 20;
char *str_nombre = "Ana";
}
