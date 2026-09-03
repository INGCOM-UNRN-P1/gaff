/*
 * REGLA 0x4005h: Evitá el uso de offsets y posiciones fijas codificadas a mano en archivos binarios sin validar sus dimensiones
 *
 * Categoria: Gestión de Archivos y Errores (0x40XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Cuando leés o escribís en una posición específica de un archivo binario mediante `fseek`, debés validar que la posición de destino sea válida y no exceda las dimensiones físicas del archivo. Calculá el tamaño del archivo usando `fseek` y `ftell` antes de realizar saltos aleatorios.
 *
 * Ejemplo canónico correcto según cátedra:
 * if (offset < tamano_archivo) { fseek(f, offset, SEEK_SET); }
 */

void test_violacion(void)
{
    fseek(f, 1000, SEEK_SET);
}
