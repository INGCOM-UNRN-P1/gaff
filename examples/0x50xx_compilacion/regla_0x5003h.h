/*
 * REGLA 0x5003h: Utilizá guardas de inclusión en todos los archivos de cabecera
 *
 * Categoria: Compilación y Buenas Prácticas de Ingeniería (0x50XX)
 * Autofix disponible: Sí
 *
 * Descripcion:
 * Todos los archivos de cabecera (`.h`) deben incluir guardas de preprocesador para evitar problemas de redefinición múltiple.
 *
 * Ejemplo canónico correcto según cátedra:
 * [Usar #pragma once o guardas #ifndef al inicio del archivo]
 */

/* Cabecera sin guardas de inclusion */
void funcion_sin_guardas(void);
