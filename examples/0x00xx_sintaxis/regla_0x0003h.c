/*
 * REGLA 0x0003h: Siempre debés inicializar las variables a un valor conocido
 *
 * Categoria: Sintaxis Básica y Nomenclatura (0x00XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Es imperativo que una variable utilizada como R-Value contenga un valor conocido antes de su uso. Aunque un sistema operativo moderno pueda inicializar la memoria en `0`, la reutilización de la misma puede introducir valores residuales. No debés confiar en una inicialización implícita.
 *
 * Ejemplo canónico correcto según cátedra:
 * int contador = 0;
 * struct datos_t d = {0};
 */

void test_violacion(void)
{
    int contador;
struct datos_t d;
}
