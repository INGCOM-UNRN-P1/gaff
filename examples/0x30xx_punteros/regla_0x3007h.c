/*
 * REGLA 0x3007h: Los argumentos de tipo puntero deben ser const siempre que la función no los modifique
 *
 * Categoria: Punteros y Gestión de Memoria (0x30XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Usar `const` en los parámetros de tipo puntero establece un contrato de solo lectura, previniendo efectos secundarios no deseados sobre los datos de origen.
 *
 * Ejemplo canónico correcto según cátedra:
 * void imprimir_texto(const char *cadena);
 */

void imprimir_texto(char *cadena);
