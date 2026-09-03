/*
 * REGLA 0x3005h: Minimizá el uso de múltiples niveles de indirección (punteros a punteros)
 *
 * Categoria: Punteros y Gestión de Memoria (0x30XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Los punteros a punteros (`**`) o de niveles superiores de indirección complican la lectura y el razonamiento sobre la memoria. Deben evitarse siempre que no sean estrictamente requeridos.
 *
 * Ejemplo canónico correcto según cátedra:
 * int *obtener_datos(size_t *tamano);
 */

void obtener_datos(int ***ptr_datos);
