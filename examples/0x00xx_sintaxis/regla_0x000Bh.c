/*
 * REGLA 0x000Bh: Las llaves deben ubicarse en líneas independientes según el estilo Allman
 *
 * Categoria: Sintaxis Básica y Nomenclatura (0x00XX)
 * Autofix disponible: Sí
 *
 * Descripcion:
 * El código debe estructurarse siguiendo el [estilo de indentación Allman](https://en.wikipedia.org/wiki/Indentation_style#Allman_style) (también conocido como estilo BSD). En este estilo: - La llave de apertura `{` asociada a una función, estructura de control o bloque de código debe ubicarse en una nueva línea, alineada en la misma columna que la sentencia contenedora. - Las sentencias contenidas dentro del bloque se indentan a cuatro espacios respecto a las llaves. - La llave de cierre `}` se coloca en una línea independiente, alineada verticalmente con su correspondiente llave de apertura. - Esto aplica de manera uniforme a definiciones de funciones, condicionales (`if`, `else if`, `else`), lazos (`while`, `for`, `do-while`), sentencias `switch`, estructuras (`struct`) y enumeraciones (`enum`). Para más detalles sobre los fundamentos y variantes de este estándar, consultá el artículo sobre [Allman style en Wikipedia](https://en.wikipedia.org/wiki/Indentation_style#Allman_style).
 *
 * Ejemplo canónico correcto según cátedra:
 * if (x > 0)
 * {
 *     return x;
 * }
 */

void test_violacion(void)
{
    if (x > 0) {
    return x;
}
}
