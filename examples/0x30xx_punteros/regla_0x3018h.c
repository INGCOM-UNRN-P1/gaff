/*
 * REGLA 0x3018h: Prohibición de invocar free() sobre punteros declarados con calificador const
 *
 * Categoria: Punteros y Gestión de Memoria (0x30XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Pasar un puntero constante a free() (incluso con cast de descarte) indica que la memoria no es de propiedad modificable o proviene de segmentos estáticos/text de sólo lectura.
 *
 * Ejemplo canónico correcto según cátedra:
 * char *buffer = malloc(32);
 * free(buffer);
 * buffer = NULL;
 */

void liberar_constante(void)
{
    const char *fijo = "cadena";
    free((void *)fijo);
}
