/*
 * REGLA 0x5006h: Preferí fgets sobre gets y scanf para leer cadenas
 *
 * Categoria: Compilación y Buenas Prácticas de Ingeniería (0x50XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * `fgets` previene el desbordamiento de búfer de entrada de forma automática mediante la validación de tamaño del buffer de entrada.
 *
 * Ejemplo canónico correcto según cátedra:
 * fgets(buffer, sizeof(buffer), stdin);
 */

void test_violacion(void)
{
    gets(buffer);
scanf("%s", buffer);
}
