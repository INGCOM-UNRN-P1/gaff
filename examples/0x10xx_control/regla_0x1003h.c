/*
 * REGLA 0x1003h: Utilizá el lazo for para iteraciones con rango o contador definido y while para lazos controlados por condiciones lógicas
 *
 * Categoria: Estructuras de Control y Lazos (0x10XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Utilizá el lazo `for` cuando la cantidad de iteraciones esté predefinida o se controle mediante un contador o rango conocido. Reservá el uso del lazo `while` para iteraciones basadas en condiciones puramente lógicas o eventos indefinidos en tiempo de ejecución. El lazo `for` es preferible para conteos, ya que agrupa la inicialización, la condición de parada y el incremento en un único lugar, previniendo lazos infinitos por olvido del incremento de control.
 *
 * Ejemplo canónico correcto según cátedra:
 * while (numero != 0) { scanf("%d", &numero); }
 */

void test(int cond)
{
    for (; cond;)
    {
        printf("infinito");
    }
}
