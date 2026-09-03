/*
 * REGLA 0x500Dh: Prohibición de redefinir palabras clave o tipos primitivos de C con #define
 *
 * Categoria: Compilación y Buenas Prácticas de Ingeniería (0x50XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Está estrictamente prohibido alterar la semántica básica del lenguaje mediante macros que redefinan palabras clave como 'if', 'for', 'int', 'return', etc.
 *
 * Ejemplo canónico correcto según cátedra:
 * #define BOOLEAN_TRUE 1
 */

#define if while
#define int long
