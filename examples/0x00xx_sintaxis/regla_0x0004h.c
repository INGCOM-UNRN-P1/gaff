/*
 * REGLA 0x0004h: Un espacio antes y después de cada operador binario
 *
 * Categoria: Sintaxis Básica y Nomenclatura (0x00XX)
 * Autofix disponible: Sí
 *
 * Descripcion:
 * Debe dejarse un espacio en blanco entre la palabra clave de control y el paréntesis ('if (', 'for (', 'while (', 'switch (') y alrededor de operadores binarios.
 *
 * Ejemplo canónico correcto según cátedra:
 * uno = dos + tres;
 */

void test(int x)
{
    if(x > 0) {
        return;
    }
}
