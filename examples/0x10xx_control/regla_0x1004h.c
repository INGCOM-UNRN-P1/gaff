/*
 * REGLA 0x1004h: Las condiciones complejas deben ser simplificadas o comentadas Si una
 *
 * Categoria: Estructuras de Control y Lazos (0x10XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * condición contiene múltiples operadores lógicos,     considerá dividirla en partes más pequeñas usando variables lógicas             auxiliares explicativas o funciones de validación.-         **Incorrecto(difícil de leer)     : ** ```` c if ((usuario_activo && tiene_permisos) ||             (es_admin && !modo_mantenimiento)) {     // ... } ```` <!-- c -->
 *
 * Ejemplo canónico correcto según cátedra:
 * bool es_valido = usuario_activo && tiene_permisos;
 * if (es_valido) { ... }
 */

void f(int a, int b, int c, int d)
{
    if (a > 0 && b > 0 && c > 0 || d > 0)
    {
        return;
    }
}
