/*
 * REGLA 0x0011h: En archivos .c la inclusión de la cabecera propia debe figurar en primer lugar
 *
 * Categoria: 0x00xx_sintaxis
 * Autofix disponible: No
 *
 * Descripcion:
 * En modulo.c, '#include "modulo.h"' debe ser la primera inclusión de usuario para asegurar que el header sea autosuficiente.
 *
 * Ejemplo canónico correcto según cátedra:
 * #include "mi_modulo.h"
 * #include <stdio.h>
 */

#include <stdio.h>
#include "otro.h"
#include "regla_0x0011h.h"
void foo(void) {}
