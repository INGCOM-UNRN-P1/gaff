/*
 * REGLA 0x200Ah: Los nombres de funciones y procedimientos deben usar snake_case en minúsculas
 *
 * Categoria: Funciones y Modularización (0x20XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Mejora la consistencia y legibilidad, distinguiendo funciones de tipos y constantes.
 *
 * Ejemplo canónico correcto según cátedra:
 * int calcular_total(int base, int impuesto);
 */

int calcularPromedio(int a, int b) {
    return (a + b) / 2;
}
