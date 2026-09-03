/*
 * REGLA 0x000Fh: Evitá comentarios obvios, redundantes o vacíos
 *
 * Categoria: 0x00xx_sintaxis
 * Autofix disponible: Sí
 *
 * Descripcion:
 * Los comentarios deben explicar la razón o justificación del algoritmo, no repetir la sintaxis obvia ni estar vacíos (//, /* */).
 *
 * Ejemplo canónico correcto según cátedra:
 * // Ajustamos el offset por alineación de 64 bits
 * ptr += 8;
 */

void test_violacion(void)
{
    i++; // incrementa i en uno
//
/* TODO */
}
