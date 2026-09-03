/*
 * REGLA 0x5005h: Organizá la estructura de tus archivos .c de forma estándar
 *
 * Categoria: Compilación y Buenas Prácticas de Ingeniería (0x50XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Mantené la estructura de archivo ordenada en secciones progresivas para mejorar su predictibilidad: 1.  Inclusiones de bibliotecas estándar (`<stdio.h>`). 2.  Inclusiones de bibliotecas de terceros. 3.  Inclusiones de cabeceras del proyecto (`"modulo.h"`). 4.  Definición de macros y constantes (`#define`). 5.  Definiciones de tipos (`typedef`, `struct`, `enum`). 6.  Prototipos de funciones privadas (`static`). 7.  Función `main` (si aplica). 8.  Implementación de funciones públicas. 9.  Implementación de funciones privadas (`static`).
 *
 * Ejemplo canónico correcto según cátedra:
 * 1. #includes
 * 2. #defines
 * 3. typedefs
 * 4. Prototipos static
 * 5. Implementaciones
 */

void funcion_uno(void)
{
    return;
}
#include <stdio.h>
