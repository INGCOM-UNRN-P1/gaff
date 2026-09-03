/*
 * REGLA 0x500Eh: Prohibición de la biblioteca obsoleta y no estándar <conio.h> (getch, clrscr)
 *
 * Categoria: Compilación y Buenas Prácticas de Ingeniería (0x50XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * La biblioteca <conio.h> no pertenece a ANSI/ISO C ni al estándar POSIX. Funciones como getch() o clrscr() impiden la compilación en sistemas Linux y GCC moderno.
 *
 * Ejemplo canónico correcto según cátedra:
 * #include <stdio.h>
 * int c = getchar();
 * printf("\033[2J");
 */

#include <conio.h>
int main(void)
{
    getch();
    return 0;
}
