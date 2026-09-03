/*
 * REGLA 0x500Ah: Protección obligatoria de parámetros en macros funcionales mediante paréntesis
 *
 * Categoria: Compilación y Buenas Prácticas de Ingeniería (0x50XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Los parámetros en el cuerpo de una macro funcional (#define CUADRADO(x) ...) deben estar siempre encerrados entre paréntesis '((x) * (x))' para prevenir anomalías por precedencia de operadores.
 *
 * Ejemplo canónico correcto según cátedra:
 * #define MULT(a, b) ((a) * (b))
 */

#define MULT(a, b) a * b
