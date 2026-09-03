/*
 * REGLA 0x4003h: Utilizá errno, perror y strerror para reportar fallos del sistema operativo de manera precisa
 *
 * Categoria: Gestión de Archivos y Errores (0x40XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Cualquier fallo en llamadas de sistema de archivos (como fallos en `fopen`, `fread` o `fwrite`) establece un código de error global en la variable `errno` de `<errno.h>`. Debés usar `perror` o `strerror` de `<string.h>` para imprimir o formatear mensajes legibles de diagnóstico.
 *
 * Ejemplo canónico correcto según cátedra:
 * if (f == NULL) { perror("Error al abrir archivo"); }
 */

void test_violacion(void)
{
    if (f == NULL) { printf("Error\n"); }
}
