/*
 * REGLA 0x2001h: Las funciones deben usar cláusulas de guarda y retornos anticipados para evitar la anidación profunda
 *
 * Categoria: Funciones y Modularización (0x20XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Se admite el uso de retornos anticipados (`early returns`) al inicio de la función en forma de cláusulas de guarda (`guard clauses`) para validar parámetros o comprobar condiciones de error iniciales inmediatas. Esto previene la anidación profunda de bloques `if` (código en flecha) y mejora la comprensión visual del camino feliz del algoritmo. Sin embargo, en funciones más complejas donde se asignen recursos locales (memoria dinámica, archivos abiertos, sockets), se prefiere centralizar la limpieza al final de la función para evitar fugas de recursos por puntos de salida prematuros alternativos.
 *
 * Ejemplo canónico correcto según cátedra:
 * if (s == NULL) return -1;
 * if (s->activo == false) return -1;
 */

void test(int a)
{
    if (a) {
        if (a > 1) {
            if (a > 2) {
                if (a > 3) {
                    return;
                }
            }
        }
    }
}
