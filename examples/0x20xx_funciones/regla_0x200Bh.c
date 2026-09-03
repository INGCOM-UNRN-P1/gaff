/*
 * REGLA 0x200Bh: Modularización: una función no debe exceder 4 parámetros de entrada
 *
 * Categoria: Funciones y Modularización (0x20XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Las funciones que requieren más de 4 argumentos deben empaquetar sus parámetros en estructuras (struct) o TDAs para reducir el acoplamiento.
 *
 * Ejemplo canónico correcto según cátedra:
 * void crear_usuario(const struct config_usuario_t *cfg);
 */

void crear_usuario(const char *nom, const char *ape, int edad, int dni, const char *mail);
