/*
 * REGLA 0x0009h: Las líneas de código no deben exceder los 79 caracteres
 *
 * Categoria: Sintaxis Básica y Nomenclatura (0x00XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Nunca debés escribir líneas que excedan los 79 caracteres. El límite de 80 columnas es un estándar de facto que facilita la lectura y la visualización de código en paralelo. Las líneas largas fatigan la vista y requieren desplazamiento horizontal.
 *
 * Ejemplo canónico correcto según cátedra:
 * printf("Mensaje largo dividido "
 *        "en dos líneas continuas.\n");
 */

void test_violacion(void)
{
    printf("Este es un mensaje de texto extremadamente largo que supera los ochenta caracteres en una sola línea.\n");
}
