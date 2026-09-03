/*
 * REGLA 0x5007h: Inclusiones redundantes o duplicadas de la misma cabecera #include
 *
 * Categoria: Compilación y Buenas Prácticas de Ingeniería (0x50XX)
 * Autofix disponible: Sí
 *
 * Descripcion:
 * No incluir dos veces el mismo archivo de cabecera en una misma unidad de traducción.
 *
 * Ejemplo canónico correcto según cátedra:
 * #include <stdio.h>
 * #include <stdlib.h>
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdio.h>
