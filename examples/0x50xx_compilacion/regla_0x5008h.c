/*
 * REGLA 0x5008h: Prohibición de funciones obsoletas o inseguras (gets, atoi)
 *
 * Categoria: Compilación y Buenas Prácticas de Ingeniería (0x50XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * El uso de gets() está estrictamente prohibido (eliminado en C11). atoi() no detecta errores de conversión; debe utilizarse strtol().
 *
 * Ejemplo canónico correcto según cátedra:
 * fgets(buf, sizeof(buf), stdin);
 * long val = strtol(str, &fin, 10);
 */

void test_violacion(void)
{
    gets(buf);
int val = atoi(str);
}
