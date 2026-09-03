/*
 * REGLA 0x0035h: Diseñá los Tipos de Datos Abstractos utilizando punteros opacos
 *
 * Categoria: Punteros y Gestión de Memoria (0x30XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Los Tipos de Datos Abstractos (TAD) deben diseñarse ocultando su representación física de datos mediante punteros opacos. La cabecera pública `.h` solo debe exponer la declaración del tipo incompleto y las firmas de sus funciones de interfaz. Toda la estructura interna y los detalles de implementación deben definirse en el archivo `.c` correspondiente.
 *
 * Ejemplo canónico correcto según cátedra:
 * typedef struct lista_t lista_t; // En lista.h
 */

struct nodo_privado
{
    int dato;
    struct nodo_privado *sig;
};
