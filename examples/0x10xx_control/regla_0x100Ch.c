/*
 * REGLA 0x100Ch: Exigencia de break explícito o comentario de fallthrough en bloques switch case
 *
 * Categoria: Estructuras de Control y Lazos (0x10XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Cada cláusula 'case' no vacía en una instrucción 'switch' debe finalizar con 'break;' o 'return;'. Si la caída es deliberada, debe documentarse con '// fallthrough'.
 *
 * Ejemplo canónico correcto según cátedra:
 * case 1:
 *     procesar();
 *     break;
 * case 2:
 *     return;
 */

void test_violacion(void)
{
    case 1:
    procesar();
case 2:
    otro();
}
