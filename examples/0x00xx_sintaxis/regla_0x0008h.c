/*
 * REGLA 0x0008h: Las constantes (const o #define) deben nombrarse en MAYUSCULAS_SNAKE_CASE
 *
 * Categoria: Sintaxis Básica y Nomenclatura (0x00XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Esta convención de estilo de nomenclatura mejora la legibilidad. Un identificador en mayúsculas actúa como una señal visual inmediata, indicando que se trata de un valor inmutable.
 *
 * Ejemplo canónico correcto según cátedra:
 * #define BUFFER_MAX 1024
 * const int DIAS_SEMANA = 7;
 */

#define buffer_max 1024
const int diasSemana = 7;
