/*
 * REGLA 0x0012h: Las variables globales deben ser declaradas como static o usar prefijo g_
 *
 * Categoria: 0x00xx_sintaxis
 * Autofix disponible: No
 *
 * Descripcion:
 * Las variables con alcance de archivo deben restringirse con static o usar explícitamente el prefijo g_ para visibilizar el acoplamiento global.
 *
 * Ejemplo canónico correcto según cátedra:
 * static int g_contador_llamadas = 0;
 */

int contador_invalido = 0;
int main(void) { return 0; }
