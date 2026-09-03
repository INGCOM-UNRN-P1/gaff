/*
 * REGLA 0x2010h: Prohibición de sombreado de parámetros mediante variables locales con el mismo nombre
 *
 * Categoria: Funciones y Modularización (0x20XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Declarar una variable local con el mismo identificador que un parámetro de la función oculta (shadows) el argumento recibido y propicia errores de asignación engañosa.
 *
 * Ejemplo canónico correcto según cátedra:
 * void procesar(int cantidad) {
 *     int factor = cantidad * 2;
 * }
 */

void procesar_dato(int cantidad)
{
    int cantidad = 10;
    (void)cantidad;
}
