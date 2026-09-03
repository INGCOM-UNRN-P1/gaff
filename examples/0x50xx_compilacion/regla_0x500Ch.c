/*
 * REGLA 0x500Ch: Prohibición de inclusión directa de archivos de código fuente C (.c)
 *
 * Categoria: Compilación y Buenas Prácticas de Ingeniería (0x50XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Nunca incluir archivos con extensión '.c' mediante '#include'. Viola los principios de compilación separada y produce errores de símbolos duplicados en el enlazador (ld).
 *
 * Ejemplo canónico correcto según cátedra:
 * #include "modulo.h"
 */

#include "modulo.c"
