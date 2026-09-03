/*
 * REGLA 0x4002h: Validá los retornos de las operaciones de lectura y escritura de archivos
 *
 * Categoria: Gestión de Archivos y Errores (0x40XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Funciones como `fread`, `fwrite`, `fgetc`, `fgets`, `fprintf` y `fscanf` devuelven valores de control. Es obligatorio verificar dichos retornos para asegurar transferencias completas e identificar fallos o el fin de archivo (EOF).
 *
 * Ejemplo canónico correcto según cátedra:
 * size_t leidos = fread(buf, 1, 100, f);
 * if (leidos < 100) { ... }
 */

void test_violacion(void)
{
    fread(buf, 1, 100, f); // Sin verificar si leyó
}
