# Catálogo de Reglas y Antipatrones de Cátedra (GAFF)

Este catálogo documenta de forma exhaustiva las reglas de estilo arquitectónico y antipatrones auditados por GAFF.

```{tableofcontents}
```

| Código | Título | Categoría |
|--------|--------|-----------|
| [0x0000h](0x0000h.md) | La claridad y prolijidad son de máxima importancia | Sintaxis Básica y Nomenclatura (0x00XX) |
| [0x0001h](0x0001h.md) | Los identificadores deben ser descriptivos | Sintaxis Básica y Nomenclatura (0x00XX) |
| [0x0002h](0x0002h.md) | Una declaración de variable por línea | Sintaxis Básica y Nomenclatura (0x00XX) |
| [0x0003h](0x0003h.md) | Siempre debés inicializar las variables a un valor conocido | Sintaxis Básica y Nomenclatura (0x00XX) |
| [0x0004h](0x0004h.md) | Un espacio antes y después de cada operador binario | Sintaxis Básica y Nomenclatura (0x00XX) |
| [0x0005h](0x0005h.md) | Cada bloque debe tener una indentación de cuatro espacios respecto a su contenedor y llaves | Sintaxis Básica y Nomenclatura (0x00XX) |
| [0x0006h](0x0006h.md) | El asterisco de los punteros debe declararse junto al identificador | Sintaxis Básica y Nomenclatura (0x00XX) |
| [0x0007h](0x0007h.md) | Los argumentos de función y las variables locales deben usar snake_case en minúsculas | Sintaxis Básica y Nomenclatura (0x00XX) |
| [0x0008h](0x0008h.md) | Las constantes (const o #define) deben nombrarse en MAYUSCULAS_SNAKE_CASE | Sintaxis Básica y Nomenclatura (0x00XX) |
| [0x0009h](0x0009h.md) | Las líneas de código no deben exceder los 79 caracteres | Sintaxis Básica y Nomenclatura (0x00XX) |
| [0x000Ah](0x000Ah.md) | Escribí comentarios que expliquen el "porqué", no el "qué" | Sintaxis Básica y Nomenclatura (0x00XX) |
| [0x000Bh](0x000Bh.md) | Las llaves deben ubicarse en líneas independientes según el estilo Allman | Sintaxis Básica y Nomenclatura (0x00XX) |
| [0x000Ch](0x000Ch.md) | Los nombres de los archivos deben usar snake_case en minúsculas (sin espacios) | General |
| [0x000Dh](0x000Dh.md) | No dejes código comentado (dead code) en los archivos fuente | General |
| [0x000Eh](0x000Eh.md) | Los nombres de funciones deben usar snake_case estricto en minúsculas | General |
| [0x000Fh](0x000Fh.md) | Evitá comentarios obvios, redundantes o vacíos | General |
| [0x0010h](0x0010h.md) | Control de longitud máxima de archivos de código (máx 500 líneas) | General |
| [0x0011h](0x0011h.md) | En archivos .c la inclusión de la cabecera propia debe figurar en primer lugar | General |
| [0x0012h](0x0012h.md) | Las variables globales deben ser declaradas como static o usar prefijo g_ | General |
| [0x0013h](0x0013h.md) | Las macros #define deben nombrarse en MAYUSCULAS_SNAKE_CASE | Sintaxis Básica y Nomenclatura (0x00XX) |
| [0x0014h](0x0014h.md) | Prohibición de identificadores con caracteres no ASCII (acentos, ñ) | Sintaxis Básica y Nomenclatura (0x00XX) |
| [0x0015h](0x0015h.md) | Alineación vertical consistente en asignaciones y declaraciones consecutivas | Sintaxis Básica y Nomenclatura (0x00XX) |
| [0x0016h](0x0016h.md) | Prohibición de identificadores que colisionen con palabras clave o tipos estándar | Sintaxis Básica y Nomenclatura (0x00XX) |
| [0x0017h](0x0017h.md) | Espaciado consistente en declaraciones de doble puntero (tipo **var) | Sintaxis Básica y Nomenclatura (0x00XX) |
| [0x0018h](0x0018h.md) | Prohibición de identificadores con prefijos reservados para el compilador (__ o _[A-Z]) | Sintaxis Básica y Nomenclatura (0x00XX) |
| [0x0019h](0x0019h.md) | Prohibición de espacios en blanco antes de separadores de sintaxis (; y ,) | Sintaxis Básica y Nomenclatura (0x00XX) |
| [0x001Ah](0x001Ah.md) | Prohibición de espacios en blanco alrededor de operadores de acceso a miembros (-> y .) | Sintaxis Básica y Nomenclatura (0x00XX) |
| [0x001Bh](0x001Bh.md) | Prohibición de espacios en blanco entre operadores unarios (++, --, !) y su operando | Sintaxis Básica y Nomenclatura (0x00XX) |
| [0x001Ch](0x001Ch.md) | Espacio en blanco obligatorio tras la coma separadora en listas y argumentos | Sintaxis Básica y Nomenclatura (0x00XX) |
| [0x001Dh](0x001Dh.md) | Prohibición de espacios en blanco internos inmediatamente tras '(' o antes de ')' | Sintaxis Básica y Nomenclatura (0x00XX) |
| [0x001Eh](0x001Eh.md) | Prohibición de múltiples espacios en blanco consecutivos dentro de una línea de código | Sintaxis Básica y Nomenclatura (0x00XX) |
| [0x001Fh](0x001Fh.md) | Prohibición de llaves redundantes en inicialización de tipos escalares | Sintaxis Básica y Nomenclatura (0x00XX) |
| [0x0020h](0x0020h.md) | Proporcionalidad en longitud de identificadores según su alcance | Sintaxis Básica y Nomenclatura (0x00XX) |
| [0x0022h](0x0022h.md) | Validador de espaciado estricto en sentencias de control | Sintaxis Básica y Nomenclatura (0x00XX) |
| [0x0023h](0x0023h.md) | Detector de variables locales no inicializadas con modificador const | Sintaxis Básica y Nomenclatura (0x00XX) |
| [0x0025h](0x0025h.md) | Validador de formato canónico en firmas de punteros a función | Sintaxis Básica y Nomenclatura (0x00XX) |
| [0x0026h](0x0026h.md) | Auditor de identificadores reservados con doble guion bajo o guion bajo inicial | Sintaxis Básica y Nomenclatura (0x00XX) |
| [0x0027h](0x0027h.md) | Validador de presencia de cabecera de documentación obligatoria por archivo | Sintaxis Básica y Nomenclatura (0x00XX) |
| [0x0028h](0x0028h.md) | Detector de etiquetas de salto goto no alineadas al margen izquierdo | Sintaxis Básica y Nomenclatura (0x00XX) |
| [0x0029h](0x0029h.md) | Auditor de inicialización de arreglos unidimensionales con exceso de elementos | Sintaxis Básica y Nomenclatura (0x00XX) |
| [0x002Bh](0x002Bh.md) | Validador de espaciado en listas de argumentos y llamadas a funciones | Sintaxis Básica y Nomenclatura (0x00XX) |
| [0x002Ch](0x002Ch.md) | Auditor de consistencia en nombres de constantes simbólicas | Sintaxis Básica y Nomenclatura (0x00XX) |
| [0x002Dh](0x002Dh.md) | Validador de espaciado en operadores unarios | Sintaxis Básica y Nomenclatura (0x00XX) |
| [0x0035h](0x0035h.md) | Diseñá los Tipos de Datos Abstractos utilizando punteros opacos | Punteros y Gestión de Memoria (0x30XX) |
| [0x0036h](0x0036h.md) | Asigná NULL al puntero tras liberar un recurso opaco en el ámbito del cliente | Punteros y Gestión de Memoria (0x30XX) |
| [0x0037h](0x0037h.md) | Evitá identificadores genéricos con sufijo numérico o afijos (numero1, num_1, n_a, a_n) | General |
| [0x0038h](0x0038h.md) | Prohibición de constantes numéricas mágicas en índices de arreglos | Sintaxis Básica y Nomenclatura (0x00XX) |
| [0x1001h](0x1001h.md) | Todas las estructuras de control deben utilizar llaves | Estructuras de Control y Lazos (0x10XX) |
| [0x1002h](0x1002h.md) | Evitá el uso descontrolado de break y continue; preferí lazos con bandera de control | Estructuras de Control y Lazos (0x10XX) |
| [0x1003h](0x1003h.md) | Utilizá el lazo for para iteraciones con rango o contador definido y while para lazos controlados por condiciones lógicas | Estructuras de Control y Lazos (0x10XX) |
| [0x1004h](0x1004h.md) | Las condiciones complejas deben ser simplificadas o comentadas Si una | Estructuras de Control y Lazos (0x10XX) |
| [0x1005h](0x1005h.md) | Evitá las condiciones ambiguas basadas en la "veracidad" (truthiness) del tipo de dato | Estructuras de Control y Lazos (0x10XX) |
| [0x1006h](0x1006h.md) | No utilizar la instrucción goto | Estructuras de Control y Lazos (0x10XX) |
| [0x1007h](0x1007h.md) | No utilizar el operador condicional (ternario) ?: | Estructuras de Control y Lazos (0x10XX) |
| [0x1008h](0x1008h.md) | Toda instrucción switch debe incluir un caso default | Estructuras de Control y Lazos (0x10XX) |
| [0x100Ah](0x100Ah.md) | Prohibición de asignaciones simples dentro de condiciones lógicas | Estructuras de Control y Lazos (0x10XX) |
| [0x100Bh](0x100Bh.md) | Prohibición de estructuras de control con cuerpo vacío (if (...);) | Estructuras de Control y Lazos (0x10XX) |
| [0x100Ch](0x100Ch.md) | Evitar comparaciones en estilo Yoda ('CONST == variable') | Estructuras de Control y Lazos (0x10XX) |
| [0x100Dh](0x100Dh.md) | Prohibición de casts de tipo innecesarios o redundantes | Estructuras de Control y Lazos (0x10XX) |
| [0x100Eh](0x100Eh.md) | Espaciado obligatorio alrededor de operadores ternarios ('? :') | Estructuras de Control y Lazos (0x10XX) |
| [0x100Fh](0x100Fh.md) | Prohibición de condiciones de parada compuestas complejas en lazos for | Estructuras de Control y Lazos (0x10XX) |
| [0x1010h](0x1010h.md) | Delimitación obligatoria con bloque de llaves en lazos do-while | Estructuras de Control y Lazos (0x10XX) |
| [0x1011h](0x1011h.md) | Prohibición de cláusula else redundante tras sentencia de retorno anticipado | Estructuras de Control y Lazos (0x10XX) |
| [0x1012h](0x1012h.md) | Prohibición de comparaciones encadenadas no idiomáticas en C (a < b < c) | Estructuras de Control y Lazos (0x10XX) |
| [0x1013h](0x1013h.md) | Prohibición de saltos no estructurados goto fuera del patrón canónico de liberación de recursos | Estructuras de Control y Lazos (0x10XX) |
| [0x1014h](0x1014h.md) | Prohibición de expresiones de asignación dentro de estructuras de control | Estructuras de Control y Lazos (0x10XX) |
| [0x1016h](0x1016h.md) | Detector de expresiones booleanas complejas sin paréntesis aclaratorios | Estructuras de Control y Lazos (0x10XX) |
| [0x1017h](0x1017h.md) | Detector de operadores de incremento o decremento múltiples en una misma expresión | Estructuras de Control y Lazos (0x10XX) |
| [0x2001h](0x2001h.md) | Las funciones deben usar cláusulas de guarda y retornos anticipados para evitar la anidación profunda | Funciones y Modularización (0x20XX) |
| [0x2002h](0x2002h.md) | Las funciones no deben contener printf o scanf, a menos que ese sea su propósito explícito | Funciones y Modularización (0x20XX) |
| [0x2003h](0x2003h.md) | Todas las funciones deben incluir documentación completa y estructurada | Funciones y Modularización (0x20XX) |
| [0x2004h](0x2004h.md) | No se permite el uso de variables globales | Funciones y Modularización (0x20XX) |
| [0x2005h](0x2005h.md) | Cada función debe tener una única responsabilidad (Principio de Responsabilidad Única) | Funciones y Modularización (0x20XX) |
| [0x2006h](0x2006h.md) | Una aserción por cada función de prueba | Funciones y Modularización (0x20XX) |
| [0x2007h](0x2007h.md) | Mantené el alcance de las variables al mínimo posible | Funciones y Modularización (0x20XX) |
| [0x2008h](0x2008h.md) | Los valores de retorno numéricos deben definirse como constantes de preprocesador o enums | Funciones y Modularización (0x20XX) |
| [0x2009h](0x2009h.md) | Los ejercicios deben ser resueltos mediante funciones | Funciones y Modularización (0x20XX) |
| [0x200Ah](0x200Ah.md) | Los nombres de funciones y procedimientos deben usar snake_case en minúsculas | Funciones y Modularización (0x20XX) |
| [0x200Bh](0x200Bh.md) | Modularización: una función no debe exceder 4 parámetros de entrada | Funciones y Modularización (0x20XX) |
| [0x200Ch](0x200Ch.md) | Prohibición de retornar la dirección de una variable local de stack | Funciones y Modularización (0x20XX) |
| [0x200Dh](0x200Dh.md) | Cada función debe tener a lo sumo un return | Funciones y Modularización (0x20XX) |
| [0x200Eh](0x200Eh.md) | Comentarios de cierre explicativos en bloques de control extensos (> 25 líneas) | Funciones y Modularización (0x20XX) |
| [0x200Fh](0x200Fh.md) | Uso obligatorio de 'void' explícito en funciones sin parámetros | Funciones y Modularización (0x20XX) |
| [0x2010h](0x2010h.md) | Prohibición de paréntesis superfluos en sentencia return | Funciones y Modularización (0x20XX) |
| [0x2011h](0x2011h.md) | Prohibición de reasignar o modificar parámetros recibidos por valor dentro de la función | Funciones y Modularización (0x20XX) |
| [0x2012h](0x2012h.md) | Prohibición de asignaciones múltiples a una variable sin lectura intermedia (dead store) | Funciones y Modularización (0x20XX) |
| [0x2013h](0x2013h.md) | Tipo de retorno obligatorio 'int' en la función main() | Funciones y Modularización (0x20XX) |
| [0x2016h](0x2016h.md) | Detector de bloques else superfluos tras sentencias terminales | Funciones y Modularización (0x20XX) |
| [0x3001h](0x3001h.md) | Siempre verificá la asignación exitosa de memoria dinámica | Punteros y Gestión de Memoria (0x30XX) |
| [0x3002h](0x3002h.md) | Liberá siempre la memoria dinámica y asigná NULL al puntero para evitar punteros colgantes | Punteros y Gestión de Memoria (0x30XX) |
| [0x3003h](0x3003h.md) | No mezcles operaciones de asignación y comparación en una sola línea | Punteros y Gestión de Memoria (0x30XX) |
| [0x3004h](0x3004h.md) | Utilizá typedef para definir tipos de estructuras con el sufijo _t | Punteros y Gestión de Memoria (0x30XX) |
| [0x3005h](0x3005h.md) | Minimizá el uso de múltiples niveles de indirección (punteros a punteros) | Punteros y Gestión de Memoria (0x30XX) |
| [0x3006h](0x3006h.md) | Documentá la propiedad de los recursos al utilizar punteros | Punteros y Gestión de Memoria (0x30XX) |
| [0x3007h](0x3007h.md) | Los argumentos de tipo puntero deben ser const siempre que la función no los modifique | Punteros y Gestión de Memoria (0x30XX) |
| [0x3008h](0x3008h.md) | Los punteros nulos deben ser inicializados y comparados con NULL, no con 0 | Punteros y Gestión de Memoria (0x30XX) |
| [0x3009h](0x3009h.md) | Documentá explícitamente los casos en que una función puede retornar NULL | Punteros y Gestión de Memoria (0x30XX) |
| [0x300Ah](0x300Ah.md) | Utilizá cast explícito al convertir tipos de punteros | Punteros y Gestión de Memoria (0x30XX) |
| [0x300Bh](0x300Bh.md) | Usá siempre sizeof en las asignaciones de memoria dinámica, prefiriendo sizeof(*ptr) | Punteros y Gestión de Memoria (0x30XX) |
| [0x300Ch](0x300Ch.md) | Verificá siempre los límites de los arreglos antes de acceder a sus elementos | Punteros y Gestión de Memoria (0x30XX) |
| [0x300Dh](0x300Dh.md) | Utilizá enum en lugar de "números mágicos" para conjuntos de estados y valores constantes | Punteros y Gestión de Memoria (0x30XX) |
| [0x300Eh](0x300Eh.md) | Documentá explícitamente el comportamiento de las funciones al manejar punteros nulos como argumentos | Punteros y Gestión de Memoria (0x30XX) |
| [0x300Fh](0x300Fh.md) | Liberá la memoria en el orden inverso a su asignación | Punteros y Gestión de Memoria (0x30XX) |
| [0x3010h](0x3010h.md) | Las variables que representan tamaños o índices de arreglos deben ser de tipo size_t | Punteros y Gestión de Memoria (0x30XX) |
| [0x3011h](0x3011h.md) | Si una función recibe un puntero genérico para operaciones de solo lectura, la firma de la función debe utilizar const void* | Punteros y Gestión de Memoria (0x30XX) |
| [0x3012h](0x3012h.md) | Prohibición de aritmética de punteros sobre void* | Punteros y Gestión de Memoria (0x30XX) |
| [0x3013h](0x3013h.md) | Asignación de memoria con sizeof sobre puntero en lugar del tipo apuntado | Punteros y Gestión de Memoria (0x30XX) |
| [0x3014h](0x3014h.md) | Prohibición de doble liberación de memoria (double free) sobre el mismo puntero | Punteros y Gestión de Memoria (0x30XX) |
| [0x3015h](0x3015h.md) | Reallocación segura: no sobreescribir el puntero original directamente | Punteros y Gestión de Memoria (0x30XX) |
| [0x3016h](0x3016h.md) | Orden incorrecto o sospechoso de argumentos en llamadas a memset | Punteros y Gestión de Memoria (0x30XX) |
| [0x3017h](0x3017h.md) | Orden canónico de calificadores: 'const tipo' en lugar de 'tipo const' | Punteros y Gestión de Memoria (0x30XX) |
| [0x3018h](0x3018h.md) | Inicialización idiomática de agregados con {0} en lugar de memset inmediato | Punteros y Gestión de Memoria (0x30XX) |
| [0x3019h](0x3019h.md) | Prohibición de comparar punteros contra constantes numéricas distintas de NULL o cero | Punteros y Gestión de Memoria (0x30XX) |
| [0x301Ah](0x301Ah.md) | Validador de uso idiomático de tipos booleanos estándar | Tipos de Datos, Memoria y Punteros (0x30XX) |
| [0x4001h](0x4001h.md) | Manejá correctamente la apertura y cierre de archivos | Gestión de Archivos y Errores (0x40XX) |
| [0x4002h](0x4002h.md) | Validá los retornos de las operaciones de lectura y escritura de archivos | Gestión de Archivos y Errores (0x40XX) |
| [0x4003h](0x4003h.md) | Utilizá errno, perror y strerror para reportar fallos del sistema operativo de manera precisa | Gestión de Archivos y Errores (0x40XX) |
| [0x4004h](0x4004h.md) | Asegurá la simetría de recursos al abrir y cerrar archivos en el mismo nivel de abstracción | Gestión de Archivos y Errores (0x40XX) |
| [0x4005h](0x4005h.md) | Evitá el uso de offsets y posiciones fijas codificadas a mano en archivos binarios sin validar sus dimensiones | Gestión de Archivos y Errores (0x40XX) |
| [0x4006h](0x4006h.md) | Prohibición del antipatrón while (!feof(f)) para control de fin de archivo | Gestión de Archivos y Errores (0x40XX) |
| [0x4007h](0x4007h.md) | Prohibición de rutas absolutas hardcodeadas en llamadas de archivo | Gestión de Archivos y Errores (0x40XX) |
| [0x4008h](0x4008h.md) | Validación obligatoria del valor de retorno de fclose() en modo escritura | Gestión de Archivos y Errores (0x40XX) |
| [0x4009h](0x4009h.md) | Prohibición de anidar llamadas a fopen() directamente dentro de funciones de E/S | Gestión de Archivos y Errores (0x40XX) |
| [0x400Ah](0x400Ah.md) | Prohibición de operar sobre flujos de archivo tras haber invocado fclose() (use-after-close) | Gestión de Archivos y Errores (0x40XX) |
| [0x5001h](0x5001h.md) | Los arreglos estáticos deben ser creados con un tamaño fijo en tiempo de compilación | Compilación y Buenas Prácticas de Ingeniería (0x50XX) |
| [0x5002h](0x5002h.md) | Desarrollá y compilá siempre con todas las advertencias del compilador activadas | Compilación y Buenas Prácticas de Ingeniería (0x50XX) |
| [0x5003h](0x5003h.md) | Utilizá guardas de inclusión en todos los archivos de cabecera | Compilación y Buenas Prácticas de Ingeniería (0x50XX) |
| [0x5004h](0x5004h.md) | Todas las operaciones con cadenas deben ser seguras | Compilación y Buenas Prácticas de Ingeniería (0x50XX) |
| [0x5005h](0x5005h.md) | Organizá la estructura de tus archivos .c de forma estándar | Compilación y Buenas Prácticas de Ingeniería (0x50XX) |
| [0x5006h](0x5006h.md) | Preferí fgets sobre gets y scanf para leer cadenas | Compilación y Buenas Prácticas de Ingeniería (0x50XX) |
| [0x5007h](0x5007h.md) | Inclusiones redundantes o duplicadas de la misma cabecera #include | Compilación y Buenas Prácticas de Ingeniería (0x50XX) |
| [0x5008h](0x5008h.md) | Prohibición de funciones obsoletas o inseguras (gets, atoi) | Compilación y Buenas Prácticas de Ingeniería (0x50XX) |
| [0x5009h](0x5009h.md) | Prohibición de división entera no intencional asignada a flotantes | Compilación y Buenas Prácticas de Ingeniería (0x50XX) |
| [0x500Ah](0x500Ah.md) | Protección obligatoria de parámetros en macros funcionales mediante paréntesis | Compilación y Buenas Prácticas de Ingeniería (0x50XX) |
| [0x500Bh](0x500Bh.md) | Inclusión obligatoria de cabeceras estándar para funciones de la biblioteca C | Compilación y Buenas Prácticas de Ingeniería (0x50XX) |
| [0x500Ch](0x500Ch.md) | Prohibición de inclusión directa de archivos de código fuente C (.c) | Compilación y Buenas Prácticas de Ingeniería (0x50XX) |
| [0x500Dh](0x500Dh.md) | Prohibición de redefinir palabras clave o tipos primitivos de C con #define | Compilación y Buenas Prácticas de Ingeniería (0x50XX) |
| [0x500Eh](0x500Eh.md) | Prohibición de la biblioteca obsoleta y no estándar <conio.h> (getch, clrscr) | Compilación y Buenas Prácticas de Ingeniería (0x50XX) |
| [0x5011h](0x5011h.md) | Colisión de nombres de macroguardas entre archivos de cabecera distintos | Compilación y Buenas Prácticas de Ingeniería (0x50XX) |
| [0x5012h](0x5012h.md) | Prohibición de directivas #pragma no estándar o privativas | Compilación y Buenas Prácticas de Ingeniería (0x50XX) |
| [0x5013h](0x5013h.md) | Prohibición de declaraciones extern en archivos de implementación (.c) | Compilación y Buenas Prácticas de Ingeniería (0x50XX) |
| [0x5014h](0x5014h.md) | Detección de inclusiones cíclicas entre archivos de cabecera | Compilación y Buenas Prácticas de Ingeniería (0x50XX) |
| [0x5015h](0x5015h.md) | Protección obligatoria con paréntesis envolventes en expresiones de macroconstantes (#define) | Compilación y Buenas Prácticas de Ingeniería (0x50XX) |
| [0x5016h](0x5016h.md) | Inclusión explícita obligatoria de cabeceras para funciones de biblioteca estándar | Compilación y Buenas Prácticas de Ingeniería (0x50XX) |
