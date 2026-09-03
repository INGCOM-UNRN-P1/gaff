/*
 * REGLA 0x3011h: Si una función recibe un puntero genérico para operaciones de solo lectura, la firma de la función debe utilizar const void*
 *
 * Categoria: Punteros y Gestión de Memoria (0x30XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Si una función recibe un puntero genérico `void*` y no modifica el contenido de la memoria apuntada, se **debe** declarar obligatoriamente el parámetro como `const void*`. Se prohíbe pasar `void*` sin calificador `const` si la operación es de solo lectura.
 *
 * Ejemplo canónico correcto según cátedra:
 * void imprimir_hex(const void *buffer, size_t n);
 */

void imprimir_hex(void *buffer, size_t n);
