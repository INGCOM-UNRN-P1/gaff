/*
 * REGLA 0x3004h: Utilizá typedef para definir tipos de estructuras con el sufijo _t
 *
 * Categoria: Punteros y Gestión de Memoria (0x30XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Esto simplifica el manejo sintáctico del código en C. Los alias de tipo creados con `typedef` deben terminar obligatoriamente con el sufijo `_t`.
 *
 * Ejemplo canónico correcto según cátedra:
 * typedef struct nodo nodo_t;
 * typedef enum estado estado_t;
 */

typedef struct { int x; } Punto;
