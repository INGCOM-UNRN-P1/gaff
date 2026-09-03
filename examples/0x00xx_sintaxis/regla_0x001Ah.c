/*
 * REGLA 0x001Ah: Prohibición de espacios en blanco alrededor de operadores de acceso a miembros (-> y .)
 *
 * Categoria: Sintaxis Básica y Nomenclatura (0x00XX)
 * Autofix disponible: Sí
 *
 * Descripcion:
 * Los operadores de acceso a campos de estructuras y uniones ('->' y '.') no deben llevar espacios en blanco a ninguno de sus lados.
 *
 * Ejemplo canónico correcto según cátedra:
 * nodo->sig = punto.x;
 */

struct Punto { int x; };
void test(struct Punto *p)
{
    int val = p -> x;
    (void)val;
}
