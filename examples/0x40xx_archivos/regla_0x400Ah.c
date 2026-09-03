/*
 * REGLA 0x400Ah: Prohibición de operar sobre flujos de archivo tras haber invocado fclose() (use-after-close)
 *
 * Categoria: Gestión de Archivos y Errores (0x40XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Utilizar un puntero a FILE* en funciones de E/S tras haber sido cerrado con fclose() provoca violaciones de segmento y corrupción del estado del runtime.
 *
 * Ejemplo canónico correcto según cátedra:
 * FILE *f = fopen("log.txt", "r");
 * ...
 * fclose(f);
 * f = NULL;
 */

void test_uac(void)
{
    FILE *arch = fopen("datos.txt", "r");
    if (!arch) return;
    fclose(arch);
    fgetc(arch);
}
