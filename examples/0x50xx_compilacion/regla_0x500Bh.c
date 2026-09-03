/*
 * REGLA 0x500Bh: Inclusión obligatoria de cabeceras estándar para funciones de la biblioteca C
 *
 * Categoria: Compilación y Buenas Prácticas de Ingeniería (0x50XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Toda invocación a funciones estándar de C requiere la inclusión explícita de su respectiva cabecera: printf/scanf (<stdio.h>), malloc/free/exit (<stdlib.h>), strcmp/strlen (<string.h>), assert (<assert.h>).
 *
 * Ejemplo canónico correcto según cátedra:
 * [Incluir siempre la cabecera correspondiente al inicio]
 */

int main(void)
{
    printf("hola mundo\n");
    return 0;
}
