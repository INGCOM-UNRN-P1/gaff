# 📏 GAFF — Linter Pedagógico de Estilo y Arquitectura Cátedra

GAFF es un linter pedagógico de código C y cabeceras H diseñado para hacer cumplir de forma automatizada las convenciones de nomenclatura, diseño estructurado y arquitectura obligatorias de la cátedra de Programación en C.

---

## 🎯 Alcance

### Qué cubre
- Linter pedagógico de estilo y convenciones arquitectónicas obligatorias de la cátedra, cubriendo 116 reglas de catálogo (`0x00XXh` a `0x50XXh`).
- Validación de sintaxis básica y espaciado intra-línea (`0x00XXh`): sangría de 4 espacios, llaves estilo Allman, prolijidad, una variable por línea, espaciado obligatorio antes y después de operadores binarios y palabras clave (`0x0004h`), macros `#define` en mayúsculas (`0x0013h`), identificadores no ASCII (`0x0014h`), operador coma para sentencias (`0x0015h`), palabras reservadas C99/C11 (`0x0016h`), notación húngara degenerada (`0x0017h`), prefijos reservados `__` o `_[A-Z]` (`0x0018h`), espacios antes de `;` y `,` con autofix (`0x0019h`), espacios alrededor de miembros `->` y `.` con autofix (`0x001Ah`), espacios en unarios `++`, `--`, `!` con autofix (`0x001Bh`), espacio obligatorio tras coma `,` con autofix (`0x001Ch`), espacios internos en paréntesis `(` y `)` con autofix (`0x001Dh`), colapso de espacios múltiples intra-línea con autofix (`0x001Eh`) y nombres en `snake_case`.
- Control de flujo y lazos (`0x10XXh`): llaves obligatorias, simplificación de condiciones, erradicación de `goto`, desuso de ternarios, prevención de truthiness, asignaciones en condicionales (`0x100Ah`), cuerpos vacíos (`0x100Bh`), `break`/fallthrough en `switch` (`0x100Ch`), control de iteradores en `for` (`0x100Dh`), condiciones tautológicas (`0x100Eh`), condiciones complejas en `for` (`0x100Fh`), lazos `do ... while` sin llaves (`0x1010h`) y `else` redundante tras `return` (`0x1011h`).
- Modularización y funciones (`0x20XXh`): contratos Doxygen con autofix (`0x2003h`), cláusulas de guarda, una única aserción por test, límite de 4 parámetros (`0x200Bh`), prohibición de retornar punteros al stack (`0x200Ch`), prohibición de más de un `return` por función (`0x200Dh`), declaración obligatoria de `(void)` con autofix (`0x200Eh`), calificador `static` en funciones auxiliares (`0x200Fh`), sombreado de parámetros (`0x2010h`), mutación de parámetros pasados por valor (`0x2011h`) y retornos estructurados.
- Punteros y memoria dinámica (`0x30XXh`): validación inmediata contra `NULL` tras `malloc`, prevención de punteros colgantes (`free(p); p = NULL;`), reallocación segura (`0x3015h`), prohibición de aritmética sobre `void *` (`0x3012h`), `sizeof(*ptr)` en vez de `sizeof(ptr)` (`0x3013h`), double free (`0x3014h`), desreferencia inmediata sin check (`0x3016h`), `free()` en expresiones (`0x3017h`), `free()` sobre punteros `const` (`0x3018h`), punteros comparados con enteros distintos de cero (`0x3019h`), simetría y tipado `size_t`.
- Gestión de archivos y errores (`0x40XXh`): validación de `fopen`, erradicación del antipatrón `while (!feof(f))` (`0x4006h`), rutas absolutas (`0x4007h`), chequeo de retorno de `fclose` en escritura (`0x4008h`), `fopen` anidado en E/S (`0x4009h`), prevención de use-after-close tras `fclose()` (`0x400Ah`), verificación de retornos de `fread`/`fwrite`, uso de `perror`/`strerror`/`errno`, simetría y offsets de `fseek`.
- Buenas prácticas de compilación (`0x50XXh`): guardas en cabeceras, deduplicación de inclusiones con autofix (`0x5007h`), prohibición de funciones obsoletas (`gets`, `atoi`) (`0x5008h`), advertencia de división entera a flotante (`0x5009h`), paréntesis en macros (`0x500Ah`), cabeceras estándar requeridas (`0x500Bh`), prohibición de incluir archivos `.c` (`0x500Ch`), prohibición de redefinir keywords con `#define` (`0x500Dh`), erradicación de `<conio.h>` (`0x500Eh`), cadenas seguras y orden canónico.
- Formateo automático de código C mediante archivo de configuración `.clang-format` institucional.
- Árbol de ejemplos canónicos (`examples/`) con un archivo para cada una de las 116 reglas verificadas.

### Qué no cubre (Límites y Delegación)
- Auditoría profunda de vulnerabilidades de seguridad de memoria o llamadas a funciones prohibidas complejas (delegado a `kaneda`).
- Fuzzing de memoria extrema (delegado a `drake`).
- Verificación formal con Frama-C (delegado a `callahan`).

---

## 📋 Requisitos

### Requisitos de Sistema y Entorno
- Multiplataforma. Python >= 3.10.

### Dependencias Externas y Binarios
- `clang-format` (opcional, para modo `--fix`).

### Integración en el Ecosistema
- CLI `gaff`. Plugin registrado en `ripley.plugins` (`style`).

---

## Reglas Principales

- **`0x0001h`**: Identificadores descriptivos (sin variables cortas no canónicas).
- **`0x0007h`**: Nombres de variables y funciones en `snake_case`.
- **`0x3004h`**: Nombres de `typedef` con prefijo `t_` o sufijo `_t`.
- **`0x2004h`**: Prohibición de variables globales mutables fuera de funciones.
- **`0x2005h`**: Longitud máxima de función $\le 50$ líneas.
- **`0x5003h`**: Guardas de inclusión obligatorias en cabeceras `.h` *(Autofix)*.
- **`0x300Dh`**: Prohibición de números mágicos sin constante definida.
- **`0x0004h`**: Espaciado correcto de palabras clave `if (`, `for (` *(Autofix)*.
- **`0x1006h`**: Prohibición de la sentencia `goto`.
- **`0x0009h`**: Longitud de línea $\le 100$ caracteres.
- **`0x0005h`**: Limpieza de trailing whitespace y tabuladores duros *(Autofix)*.

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
gaff explain 0x0001h
```
