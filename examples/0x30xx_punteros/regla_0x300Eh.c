/*
 * REGLA 0x300Eh: Documentá explícitamente el comportamiento de las funciones al manejar punteros nulos como argumentos
 *
 * Categoria: Punteros y Gestión de Memoria (0x30XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Si una función acepta que sus argumentos punteros sean `NULL`, se debe indicar el comportamiento esperado. Si no los acepta, se debe documentar como una precondición explícita.
 *
 * Ejemplo canónico correcto según cátedra:
 * /** @param ptr Puntero al recurso (no debe ser NULL). */
 */

/**
 * Procesa los datos del cliente.
 * @param datos Puntero a la estructura.
 */
void procesar_cliente(int *datos)
{
    *datos = 10;
}
