# 📏 GAFF — Linter Pedagógico de Estilo y Arquitectura Cátedra

GAFF es un linter pedagógico de código C y cabeceras H diseñado para hacer cumplir de forma automatizada las convenciones de nomenclatura, diseño estructurado y arquitectura obligatorias de la cátedra de Programación en C.

## Reglas Principales

- **`GAFF001`**: Nombres de variables y funciones en `snake_case`.
- **`GAFF002`**: Nombres de `typedef` con prefijo `t_` o sufijo `_t`.
- **`GAFF003`**: Prohibición de variables globales mutables fuera de funciones.
- **`GAFF004`**: Longitud máxima de función $\le 50$ líneas.
- **`GAFF005`**: Guardas de inclusión obligatorias en cabeceras `.h` *(Autofix)*.
- **`GAFF006`**: Prohibición de números mágicos sin constante definida.
- **`GAFF007`**: Espaciado correcto de palabras clave `if (`, `for (` *(Autofix)*.
- **`GAFF008`**: Prohibición de la sentencia `goto`.
- **`GAFF009`**: Longitud de línea $\le 100$ caracteres.
- **`GAFF010`**: Limpieza de trailing whitespace y tabuladores duros *(Autofix)*.

## Uso Rápido

```bash
# 1. Auditar archivos o directorios
gaff check src/ main.c

# 2. Auditar y aplicar correcciones automáticas
gaff check src/ --fix

# 3. Aplicar correcciones automáticas directamente
gaff fix src/

# 4. Salida estructurada JSON para CI/CD
gaff check src/ --json

# 5. Listar o explicar reglas del catálogo
gaff rules
gaff explain GAFF001
```
