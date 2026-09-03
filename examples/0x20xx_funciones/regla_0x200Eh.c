/*
 * REGLA 0x200Eh: Declaración explícita de (void) en funciones que no reciben parámetros
 *
 * Categoria: Funciones y Modularización (0x20XX)
 * Autofix disponible: Sí
 *
 * Descripcion:
 * En lenguaje C, una función declarada como 'f()' acepta cualquier número de argumentos sin verificación de tipos. Debe declararse explícitamente como 'f(void)'.
 *
 * Ejemplo canónico correcto según cátedra:
 * void limpiar_pantalla(void);
 */

void limpiar_pantalla();
