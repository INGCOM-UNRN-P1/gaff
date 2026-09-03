/*
 * REGLA 0x4007h: Prohibición de rutas absolutas hardcodeadas en llamadas de archivo
 *
 * Categoria: Gestión de Archivos y Errores (0x40XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * No incluir rutas locales absolutas fijas (/home/..., C:\\...) en fopen(). Usar rutas relativas o argumentos recibidos por la aplicación.
 *
 * Ejemplo canónico correcto según cátedra:
 * FILE *f = fopen("datos.csv", "r");
 */

void test_violacion(void)
{
    FILE *f = fopen("/home/usuario/datos.csv", "r");
}
