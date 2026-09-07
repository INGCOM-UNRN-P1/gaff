/*
 * REGLA 0x200Dh: Cada función debe tener a lo sumo un return
 *
 * Categoria: Funciones y Modularización (0x20XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Cada función debe estructurarse con un único punto de retorno (sentencia 'return'). El uso de múltiples 'return' dispersos dificulta el seguimiento del flujo de control y complica la liberación uniforme de recursos.
 *
 * Ejemplo canónico correcto según cátedra:
 * int calcular(int x)
 * {
 *     int resultado = 0;
 *     if (x > 0) {
 *         resultado = x * 2;
 *     }
 *     return resultado;
 * }
 */

int funcion_con_multiples_retornos(int x)
{
    if (x > 0)
    {
        return 1;
    }
    return 0;
}
