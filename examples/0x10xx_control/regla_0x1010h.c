/*
 * REGLA 0x1010h: Delimitación obligatoria con bloque de llaves en lazos do-while
 *
 * Categoria: Estructuras de Control y Lazos (0x10XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Toda estructura 'do ... while' debe encerrar su cuerpo entre llaves explícitas '{ ... }' para evitar confusiones sintácticas con sentencias while independientes.
 *
 * Ejemplo canónico correcto según cátedra:
 * do {
 *     x++;
 * } while (x < 10);
 */

void test(int x)
{
    do x++; while (x < 10);
}
