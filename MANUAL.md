# Manual de Uso y Referencia Técnica: gaff

> **GAFF** — Linter pedagógico de estilo arquitectónico y convenciones obligatorias de cátedra con autofix
> **Versión:** `0.1.0` · **CLI principal:** `gaff` · **Plugin Ripley:** `style`

---

## 1. Arquitectura y Propósito Pedagógico

`gaff` forma parte del ecosistema de herramientas de la cátedra de Programación 1 (UNRN). Su objetivo central es resolver de forma modular, determinista y automatizada las tareas asociadas a su dominio específico dentro del ciclo de desarrollo, evaluación y aprendizaje de software en C.

### Alcance Funcional (Qué cubre)
- Linter pedagógico de estilo y convenciones arquitectónicas obligatorias de la cátedra, cubriendo 219 reglas de catálogo (`0x00XXh` a `0x80XXh`).
- Validación de sintaxis básica y espaciado intra-línea (`0x00XXh`): sangría de 4 espacios, llaves estilo Allman, prolijidad, una variable por línea, espaciado obligatorio antes y después de operadores binarios y palabras clave (`0x0004h`), macros `#define` en mayúsculas (`0x0013h`), identificadores no ASCII (`0x0014h`), operador coma para sentencias (`0x0015h`), palabras reservadas C99/C11 (`0x0016h`), notación húngara degenerada (`0x0017h`), prefijos reservados `__` o `_[A-Z]` (`0x0018h`), espacios antes de `;` y `,` con autofix (`0x0019h`), espacios alrededor de miembros `->` y `.` con autofix (`0x001Ah`), espacios en unarios `++`, `--`, `!` con autofix (`0x001Bh`), espacio obligatorio tras coma `,` con autofix (`0x001Ch`), espacios internos en paréntesis `(` y `)` con autofix (`0x001Dh`), colapso de espacios múltiples intra-línea con autofix (`0x001Eh`) y nombres en `snake_case`.
- Control de flujo y lazos (`0x10XXh`): llaves obligatorias, simplificación de condiciones, erradicación de `goto`, desuso de ternarios, prevención de truthiness, asignaciones en condicionales (`0x100Ah`), cuerpos vacíos (`0x100Bh`), `break`/fallthrough en `switch` (`0x100Ch`), control de iteradores en `for` (`0x100Dh`), condiciones tautológicas (`0x100Eh`), condiciones complejas en `for` (`0x100Fh`), lazos `do ... while` sin llaves (`0x1010h`) y `else` redundante tras `return` (`0x1011h`).
- Modularización y funciones (`0x20XXh`): contratos Doxygen con autofix (`0x2003h`), cláusulas de guarda, una única aserción por test, límite de 4 parámetros (`0x200Bh`), prohibición de retornar punteros al stack (`0x200Ch`), prohibición de más de un `return` por función (`0x200Dh`), declaración obligatoria de `(void)` con autofix (`0x200Eh`), calificador `static` en funciones auxiliares (`0x200Fh`), sombreado de parámetros (`0x2010h`), mutación de parámetros pasados por valor (`0x2011h`) y retornos estructurados.
- Punteros y memoria dinámica (`0x30XXh`): validación inmediata contra `NULL` tras `malloc`, prevención de punteros colgantes (`free(p); p = NULL;`), reallocación segura (`0x3015h`), prohibición de aritmética sobre `void *` (`0x3012h`), `sizeof(*ptr)` en vez de `sizeof(ptr)` (`0x3013h`), double free (`0x3014h`), desreferencia inmediata sin check (`0x3016h`), `free()` en expresiones (`0x3017h`), `free()` sobre punteros `const` (`0x3018h`), punteros comparados con enteros distintos de cero (`0x3019h`), simetría y tipado `size_t`.
- Gestión de archivos y errores (`0x40XXh`): validación de `fopen`, erradicación del antipatrón `while (!feof(f))` (`0x4006h`), rutas absolutas (`0x4007h`), chequeo de retorno de `fclose` en escritura (`0x4008h`), `fopen` anidado en E/S (`0x4009h`), prevención de use-after-close tras `fclose()` (`0x400Ah`), verificación de retornos de `fread`/`fwrite`, uso de `perror`/`strerror`/`errno`, simetría y offsets de `fseek`.
- Buenas prácticas de compilación (`0x50XXh`): guardas en cabeceras, deduplicación de inclusiones con autofix (`0x5007h`), prohibición de funciones obsoletas (`gets`, `atoi`) (`0x5008h`), advertencia de división entera a flotante (`0x5009h`), paréntesis en macros (`0x500Ah`), cabeceras estándar requeridas (`0x500Bh`), prohibición de incluir archivos `.c` (`0x500Ch`), prohibición de redefinir keywords con `#define` (`0x500Dh`), erradicación de `<conio.h>` (`0x500Eh`), cadenas seguras y orden canónico.
- Formateo automático de código C mediante archivo de configuración `.clang-format` institucional.
- Árbol de ejemplos canónicos (`examples/`) con suites de prueba para las familias de reglas verificadas.

### Límites de Responsabilidad y Delegación (Qué no cubre)
- Auditoría profunda de vulnerabilidades de seguridad de memoria o llamadas a funciones prohibidas complejas (delegado a `kaneda`).
- Fuzzing de memoria extrema (delegado a `drake`).
- Verificación formal con Frama-C (delegado a `callahan`).

### Principios de Diseño
- **Enfoque Pedagógico:** Diagnósticos y mensajes en español rioplatense orientados a facilitar la comprensión de errores conceptuales.
- **Salida Estructurada Dual:** Soporte nativo para visualización enriquecida en terminal (Rich) y salida parseable para orquestadores (`--json`).
- **Integración Contractual:** Capacidad de emitir secciones de reporte para `dredd` (`dredd-section`) y actuar como satélite orquestado por `ripley`.
- **Idempotencia y Robustez:** Validación de precondiciones y comandos de autodiagnóstico (`doctor`) para verificación del entorno.

---

## 2. Instalación y Requisitos

### Requisitos del Sistema
- **Python:** `>= 3.10` (recomendado Python 3.11 o 3.12).
- **Gestor de paquetes:** [`uv`](https://github.com/astral-sh/uv) (entorno estándar de cátedra).
- **Toolchain C (si aplica):** GCC / Clang, Make, GDB y bibliotecas estándar de desarrollo.

### Instalación en el Entorno de Usuario
Para instalar la herramienta de forma global y aislada en el sistema mediante `uv tool`:
```bash
uv tool install --editable /home/mrtin/dev/tools/gaff
```

### Verificación de Instalación
Ejecutá el comando `doctor` para constatar que todas las dependencias y binarios requeridos estén presentes y operativos:
```bash
gaff doctor
```

---

## 3. Guía Integral de Comandos (CLI)

| Comando | Descripción Breve |
| :--- | :--- |
| [`gaff check`](#check) | Audita archivos de código C comprobando las reglas de estilo y arquitectura de la cátedra. |
| [`gaff report`](#report) | Genera directamente la sección de reporte Markdown de GAFF para Dredd. |
| [`gaff rules`](#rules) | Lista todas las reglas de estilo y arquitectura del catálogo de cátedra. |
| [`gaff explain`](#explain) | Explica en detalle una regla de cátedra con ejemplos de código correctos e incorrectos. |
| [`gaff init-config`](#initconfig) | Exporta la configuración de estilo de la cátedra (.clang-format o .gaffrc.json). |
| [`gaff fix`](#fix) | Aplica correcciones automáticas de estilo con opción de vista previa interactiva. |
| [`gaff format`](#format) | Formatea código C/H aplicando las convenciones canónicas de la cátedra. |
| [`gaff install-hook`](#installhook) | Instala un hook pre-commit de git para verificar estilo con GAFF antes de commitear. |
| [`gaff doctor`](#doctor) | Verifica dependencias externas de GAFF (clang-format, git, gcc). |
| [`gaff export-rules`](#exportrules) | Exporta el manual y catálogo oficial de reglas de estilo en formato Markdown. |
| [`gaff badge`](#badge) | Genera un badge SVG con el puntaje y estado de cumplimiento de estilo GAFF (formato Shields.io). |
| [`gaff diff`](#diff) | Audita únicamente las líneas añadidas o modificadas según git diff. |
| [`gaff lsp-quickfix`](#lspquickfix) | Genera acciones rápidas CodeAction compatibles con el protocolo LSP para editores de texto. |

### `gaff check`

Audita archivos de código C comprobando las reglas de estilo y arquitectura de la cátedra.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `rutas` | `List[Path]` | Archivos C/H o directorios a analizar. |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--recursive`, `-r` | `bool` | `False` | Procesa recursivamente todos los subdirectorios. |
| `--fix`, `-f` | `bool` | `False` | Aplica automáticamente correcciones en reglas autofixables. |
| `--exclude`, `-e`, `--ignore`, `-i` | `Optional[str]` | `None` | Lista de códigos de regla a excluir/desactivar separados por comas (ej: '0x0001h,0x0037h'). |
| `--rules`, `-R` | `Optional[str]` | `None` | [Legado/Filtro] Lista de códigos de regla a evaluar exclusivamente. Por defecto se evalúan todas salvo las excluidas. |
| `--json` | `bool` | `False` | Emitir reporte estructurado en JSON. |
| `--md`, `--output-md`, `-o` | `Optional[Path]` | `None` | Generar sección de reporte en formato Markdown para fusión en Dredd. |
| `--badge`, `-b` | `Optional[Path]` | `None` | Ruta de salida para generar un badge SVG de cumplimiento de estilo. |
| `--quiet`, `-q` | `bool` | `False` | Ocultar advertencias y solo mostrar errores críticos. |
| `--sarif` | `bool` | `False` | Emitir informe en formato estándar OASIS SARIF 2.1.0. |
| `--github-summary` | `bool` | `False` | Exportar resumen de cumplimiento en Markdown para GitHub Actions ($GITHUB_STEP_SUMMARY). |
| `--convert-guards` | `bool` | `False` | Convierte automáticamente directivas #pragma once en guardas canónicas #ifndef. |
| `--idkfa` | `bool` | `False` | Modo IDKFA: preserva intactos todos los comentarios sin formatearlos ni modificarlos. |

#### Ejemplo de Invocación
```bash
gaff check <rutas>
```

### `gaff report`

Genera directamente la sección de reporte Markdown de GAFF para Dredd.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `rutas` | `List[Path]` | Archivos C/H o directorios a analizar. |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--recursive`, `-r` | `bool` | `False` | Procesa recursivamente todos los subdirectorios. |
| `--output`, `-o` | `Optional[Path]` | `None` | Ruta de destino del archivo Markdown. |
| `--rules`, `-R` | `Optional[str]` | `None` | Reglas a habilitar. |

#### Ejemplo de Invocación
```bash
gaff report <rutas>
```

### `gaff rules`

Lista todas las reglas de estilo y arquitectura del catálogo de cátedra.

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--json`, `-j` | `bool` | `False` | Emite el catálogo completo en formato JSON versionado. |

#### Ejemplo de Invocación
```bash
gaff rules
```

### `gaff explain`

Explica en detalle una regla de cátedra con ejemplos de código correctos e incorrectos.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `codigo` | `str` | Código de cátedra de la regla a explicar (ej: '0x0001h'). |

#### Ejemplo de Invocación
```bash
gaff explain <codigo>
```

### `gaff init-config`

Exporta la configuración de estilo de la cátedra (.clang-format o .gaffrc.json).

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--dir`, `-d` | `Path` | `.` | Directorio donde generar configuración |
| `--force`, `-f` | `bool` | `False` | Sobrescribir archivo existente |
| `--gaffrc` | `bool` | `False` | Generar plantilla de configuración institucional .gaffrc.json personalizada |
| `--tp` | `str` | `TP General` | Nombre o identificación del Trabajo Práctico |
| `--catedra` | `str` | `Cátedra de Algoritmos y Programación` | Nombre de la cátedra |
| `--exclude`, `-e` | `Optional[str]` | `None` | Reglas a excluir separadas por comas |

#### Ejemplo de Invocación
```bash
gaff init-config
```

### `gaff fix`

Aplica correcciones automáticas de estilo con opción de vista previa interactiva.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `rutas` | `List[Path]` | Archivos C/H o directorios a corregir. |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--recursive`, `-r` | `bool` | `False` | Procesa recursivamente todos los subdirectorios. |
| `--rules`, `-R` | `Optional[str]` | `None` | Reglas a aplicar. |
| `--exclude`, `-e` | `Optional[str]` | `None` | Reglas a excluir separadas por comas. |
| `--interactive`, `-i` | `bool` | `False` | Previsualiza el diff de cada cambio antes de aplicar. |
| `--idkfa` | `bool` | `False` | Modo IDKFA: preserva intactos todos los comentarios sin formatearlos ni modificarlos. |

#### Ejemplo de Invocación
```bash
gaff fix <rutas>
```

### `gaff format`

Formatea código C/H aplicando las convenciones canónicas de la cátedra.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `rutas` | `List[Path]` | Archivos o directorios a formatear |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--recursive`, `-r` | `bool` | `False` | Procesa recursivamente todos los subdirectorios. |
| `--idkfa` | `bool` | `False` | Modo IDKFA: preserva intactos todos los comentarios sin formatearlos ni modificarlos. |

#### Ejemplo de Invocación
```bash
gaff format <rutas>
```

### `gaff install-hook`

Instala un hook pre-commit de git para verificar estilo con GAFF antes de commitear.

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--git-dir` | `Path` | `.git` | Directorio .git del repositorio |

#### Ejemplo de Invocación
```bash
gaff install-hook
```

### `gaff doctor`

Verifica dependencias externas de GAFF (clang-format, git, gcc).

#### Ejemplo de Invocación
```bash
gaff doctor
```

### `gaff export-rules`

Exporta el manual y catálogo oficial de reglas de estilo en formato Markdown.

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--output`, `-o` | `Optional[Path]` | `None` | Ruta de destino del archivo Markdown. |

#### Ejemplo de Invocación
```bash
gaff export-rules
```

### `gaff badge`

Genera un badge SVG con el puntaje y estado de cumplimiento de estilo GAFF (formato Shields.io).

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `rutas` | `List[Path]` | Archivos C/H o directorios a auditar para el badge. |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--output`, `-o` | `Path` | `gaff-badge.svg` | Ruta donde guardar el badge SVG. |
| `--recursive`, `-r` | `bool` | `False` | Procesa recursivamente todos los subdirectorios. |

#### Ejemplo de Invocación
```bash
gaff badge <rutas>
```

### `gaff diff`

Audita únicamente las líneas añadidas o modificadas según git diff.

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--rutas` | `Optional[List[Path]]` | `None` | Rutas o archivos a restringir el diff. |
| `--base`, `-b` | `str` | `HEAD` | Referencia base de git contra la cual comparar (ej. 'HEAD', 'main'). |
| `--fix`, `-f` | `bool` | `False` | Aplica automáticamente correcciones en reglas autofixables. |
| `--json` | `bool` | `False` | Emitir reporte estructurado en JSON. |

#### Ejemplo de Invocación
```bash
gaff diff
```

### `gaff lsp-quickfix`

Genera acciones rápidas CodeAction compatibles con el protocolo LSP para editores de texto.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `archivo` | `Path` | Archivo C/H a generar acciones rápidas LSP. |

#### Ejemplo de Invocación
```bash
gaff lsp-quickfix <archivo>
```

---

## 4. Formatos de Salida e Integración con el Ecosistema

### Modo Interactivo / Terminal (Rich)
Por defecto, la herramienta renderiza paneles, árboles y tablas estilizadas para facilitar la lectura del estudiante y docente en terminales modernas con soporte ANSI.

### Modo Estructurado JSON (`--json`)
Para integración con pipelines de CI/CD, scripts de automatización u orquestadores externos, la opción `--json` emite un documento JSON estricto por la salida estándar (`stdout`), dirigiendo cualquier mensaje de logging a `stderr`:
```bash
gaff check --json
```

### Integración con Dredd (`dredd-section`)
Cuando la herramienta genera reportes de evaluación para entregas de alumnos, produce una sección Markdown estandarizada conforme al contrato de integración de Dredd (v1.0.0):
```markdown
<!-- dredd-section: gaff, tool=gaff, version=0.1.0, status=ok -->
```
Este encabezado garantiza la agregación determinista de los hallazgos en la rúbrica docente.

### Integración con Ripley
`gaff` está registrada en el catálogo de plugins satélites de Ripley (`SATELLITE_CATALOG`). Puede invocarse directamente a través del motor de evaluación de Ripley configurando el análisis en `ripley.toml`.

---

## 5. Diagnóstico y Códigos de Salida

### Códigos de Retorno (`exit code`)
| Código | Significado |
| :---: | :--- |
| `0` | Ejecución exitosa sin hallazgos críticos ni errores de sintaxis. |
| `1` | Hallazgos pedagógicos detectados, infracción de reglas o advertencias activas. |
| `2` | Error de sintaxis en argumentos CLI o archivo fuente no encontrado. |
| `>2` | Error no recuperable del sistema, fallo de memoria o excepción interna. |

### Diagnóstico del Entorno (`doctor`)
Ante comportamientos inesperados, verificá el estado operativo con:
```bash
gaff doctor
```
Comprueba la presencia de las dependencias requeridas y la integridad de los componentes del paquete.