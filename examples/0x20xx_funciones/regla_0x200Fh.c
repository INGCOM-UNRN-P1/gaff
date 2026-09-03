/*
 * REGLA 0x200Fh: Calificador static obligatorio en funciones auxiliares privadas de archivo
 *
 * Categoria: Funciones y Modularización (0x20XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Las funciones auxiliares internas de un archivo .c que no forman parte de la interfaz pública (.h) deben declararse como 'static' para encapsular su enlace y visibilidad.
 *
 * Ejemplo canónico correcto según cátedra:
 * static int calcular_checksum(const char *buf);
 */

int helper_privado_sin_static(void)
{
    return 42;
}
