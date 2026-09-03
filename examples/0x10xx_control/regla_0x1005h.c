/*
 * REGLA 0x1005h: Evitá las condiciones ambiguas basadas en la "veracidad" (truthiness) del tipo de dato
 *
 * Categoria: Estructuras de Control y Lazos (0x10XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Las comparaciones deben ser siempre explícitas. En C, cualquier valor numérico distinto de cero se considera verdadero, y el cero falso. Depender de esta veracidad implícita atenta contra la legibilidad. Es fundamental diferenciar de forma inequívoca la comparación de caracteres del chequeo de punteros: - Si la variable es un carácter (`char`), comparalo contra el carácter nulo de cadena `'\0'`. - Si la variable es un puntero, comparalo contra `NULL`. - Si es una variable lógica, comparala contra `true` o `false`.
 *
 * Ejemplo canónico correcto según cátedra:
 * if (x != 0)
 * {
 */

void f(const char *s)
{
    if (!strcmp(s, "test"))
    {
        return;
    }
}
