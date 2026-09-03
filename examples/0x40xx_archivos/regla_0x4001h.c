/*
 * REGLA 0x4001h: Manejá correctamente la apertura y cierre de archivos
 *
 * Categoria: Gestión de Archivos y Errores (0x40XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Siempre validá que el puntero devuelto por `fopen` no sea `NULL` antes de operar sobre él, y cerrá el recurso mediante `fclose`.
 *
 * Ejemplo canónico correcto según cátedra:
 * FILE *f = fopen("datos.txt", "r");
 * if (f == NULL) return -1;
 * ...
 * fclose(f);
 */

void test_violacion(void)
{
    FILE *f = fopen("datos.txt", "r");
fread(buf, 1, 10, f); // Si f es NULL rompe
}
