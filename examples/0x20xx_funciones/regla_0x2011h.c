/*
 * REGLA 0x2011h: Prohibición de reasignar o modificar parámetros recibidos por valor dentro de la función
 *
 * Categoria: Funciones y Modularización (0x20XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Modificar un parámetro primitivo recibido por valor (ej: n = 10; n++) confunde el contrato de entrada. Copiá el valor a una variable local explícita si requerís mutabilidad.
 *
 * Ejemplo canónico correcto según cátedra:
 * int calcular(int limite) {
 *     int restante = limite;
 *     while (restante > 0) restante--;
 *     return restante;
 * }
 */

int incrementar_limite(int limite)
{
    limite++;
    return limite;
}
