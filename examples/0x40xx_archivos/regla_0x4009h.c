/*
 * REGLA 0x4009h: Prohibición de anidar llamadas a fopen() directamente dentro de funciones de E/S
 *
 * Categoria: Gestión de Archivos y Errores (0x40XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Llamar a fopen() dentro del paso de parámetros de fread/fscanf impide comprobar si el retorno fue NULL y genera fugas de recursos al no existir puntero para fclose().
 *
 * Ejemplo canónico correcto según cátedra:
 * FILE *f = fopen("data.txt", "r");
 * if (f) { fscanf(f, "%d", &x); fclose(f); }
 */

void test_violacion(void)
{
    fscanf(fopen("data.txt", "r"), "%d", &x); // anidamiento inseguro
}
