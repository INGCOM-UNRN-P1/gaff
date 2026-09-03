/*
 * REGLA 0x1011h: Prohibición de cláusula else redundante tras sentencia de retorno anticipado
 *
 * Categoria: Estructuras de Control y Lazos (0x10XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Si una rama 'if' concluye incondicionalmente con 'return;', la cláusula 'else' posterior es redundante. Desanidá el flujo para mantener bajo el nivel de indentación.
 *
 * Ejemplo canónico correcto según cátedra:
 * if (error) {
 *     return -1;
 * }
 * procesar_exito();
 * return 0;
 */

int test(int x)
{
    if (x > 0) {
        return 1;
    } else {
        return 0;
    }
}
