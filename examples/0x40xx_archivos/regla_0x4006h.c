/*
 * REGLA 0x4006h: Prohibición del antipatrón while (!feof(f)) para control de fin de archivo
 *
 * Categoria: Gestión de Archivos y Errores (0x40XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * La función 'feof()' solo retorna verdadero DESPUÉS de que una operación de lectura previa haya fallado al toparse con el fin de archivo. Usarla en la cabecera procesa el último registro dos veces.
 *
 * Ejemplo canónico correcto según cátedra:
 * while (fgets(buf, sizeof(buf), f) != NULL) {
 *     procesar(buf);
 * }
 */

void test_violacion(void)
{
    while (!feof(f)) {
    fgets(buf, sizeof(buf), f);
    procesar(buf);
}
}
