/*
 * REGLA 0x3016h: Prohibición de desreferencia directa de memoria dinámica sin check a NULL previo
 *
 * Categoria: Punteros y Gestión de Memoria (0x30XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Desreferenciar un puntero inmediatamente tras invocar malloc/calloc sin mediar un bloque condicional que verifique contra NULL arriesga segfaults directos ante escasez de memoria.
 *
 * Ejemplo canónico correcto según cátedra:
 * int *p = malloc(sizeof(int));
 * if (p == NULL) return;
 * *p = 10;
 */

void test_violacion(void)
{
    int *p = malloc(sizeof(int));
*p = 10;
}
