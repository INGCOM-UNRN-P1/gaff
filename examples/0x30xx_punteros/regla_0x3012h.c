/*
 * REGLA 0x3012h: Prohibición de aritmética de punteros sobre void*
 *
 * Categoria: Punteros y Gestión de Memoria (0x30XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * La aritmética sobre void* es inválida en C estándar ANSI/ISO ya que sizeof(void) no está definido. Debe castearse a char* o uint8_t*.
 *
 * Ejemplo canónico correcto según cátedra:
 * void *sig = (char *)ptr + salto;
 */

void test(void)
{
    void *p = malloc(10);
    p++;
}
