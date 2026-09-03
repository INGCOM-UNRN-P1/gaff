/*
 * REGLA 0x2003h: Todas las funciones deben incluir documentación completa y estructurada
 *
 * Categoria: Funciones y Modularización (0x20XX)
 * Autofix disponible: Sí
 *
 * Descripcion:
 * Una documentación adecuada define la especificación conceptual y formal del comportamiento de la función mediante etiquetas como `@param`, `@pre`, `@returns`, `@post`, e invariantes mediante `@invariant`.
 *
 * Ejemplo canónico correcto según cátedra:
 * /*
 *  * @brief Suma dos enteros.
 *  * @param a Primer sumando.
 *  * @param b Segundo sumando.
 *  * @return Resultado de la suma.
 *  */
 */





void funcion_sin_documentar(int a, int b)
{
    int c = a + b;
    (void)c;
}
