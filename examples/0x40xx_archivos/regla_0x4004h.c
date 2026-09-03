/*
 * REGLA 0x4004h: Asegurá la simetría de recursos al abrir y cerrar archivos en el mismo nivel de abstracción
 *
 * Categoria: Gestión de Archivos y Errores (0x40XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * La función que abre un archivo debe ser la misma responsable de cerrarlo, o bien se debe delegar formalmente su propiedad a una estructura/módulo administrador simétrico. Esto evita descriptores de archivo huérfanos que agoten el límite del sistema operativo.
 *
 * Ejemplo canónico correcto según cátedra:
 * void procesar() { FILE *f = fopen(...); ... fclose(f); }
 */

void test_violacion(void)
{
    FILE *f = fopen(...); delegar(f); // Nadie cierra f
}
