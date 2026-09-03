/*
 * REGLA 0x2008h: Los valores de retorno numéricos deben definirse como constantes de preprocesador o enums
 *
 * Categoria: Funciones y Modularización (0x20XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * El uso de nombres descriptivos para los valores de retorno numéricos facilita la comprensión de su significado semántico.
 *
 * Ejemplo canónico correcto según cátedra:
 * return ERROR_APERTURA_ARCHIVO;
 */

int calcular(int x)
{
    if (x < 0)
    {
        return -1;
    }
    return 42;
}
