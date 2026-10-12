# Guía del documento del proyecto de grado

Para Brahian (y para Tania si sigue leyendo). Explica qué se hizo en la copia intervenida, cómo leer las cifras y qué
falta para terminar. Actualizada: 2026-10-12.

## 1. Qué hay en esta carpeta

| Archivo | Para qué sirve |
|---|---|
| `FICHA_HECHOS.md` | Todos los datos verificados, con su fuente. Si un número no está aquí, no va al documento |
| `DIAGNOSTICO_DOCUMENTO.md` | Los 28 problemas encontrados en el Word, el presupuesto de páginas y las reglas de la plantilla USB |
| `diagramas/` | Diagramas en Mermaid (`.mmd`, editables) y en imagen (`.png`, listos para pegar) |
| `herramientas/` | Los scripts que generaron la copia intervenida (por si hay que repetirla sobre una versión nueva del Word) |

La copia intervenida del Word (`Proyecto_de_grado_Dron_IA_INTERVENIDO.docx`) y la vista previa limpia **no se suben al
repositorio** porque es público y el borrador todavía no está entregado. Se entregaron por el chat.

## 2. Cómo trabajar la copia intervenida

1. Abrirla en Word. Los colores son resaltados (no control de cambios):
   - **rojo**: sobra o está mal;
   - **verde**: reemplaza al rojo que tiene justo antes;
   - **amarillo**: texto nuevo;
   - **turquesa**: `[REVISAR: …]`, una decisión tuya.
2. Leer de arriba abajo. En cada rojo con verde al lado: si estás de acuerdo, borra el rojo y quítale el resaltado al
   verde. Si no, haz lo contrario.
3. Resolver cada turquesa y borrarlo.
4. Recrear los rótulos nuevos (Tabla N1, Figura N2…) con **Referencias > Insertar título**, para que entren en las listas
   y se numeren solos. Después, clic derecho sobre cada índice > **Actualizar campo > Actualizar toda la tabla**.
5. Borrar la leyenda amarilla del principio.

La vista previa limpia muestra cómo queda si aceptas todo: 103 páginas en total, unas 101 sin anexos.

## 3. Qué cambió y por qué (resumen)

- **Raspberry Pi → Jetson Orin Nano** en todo lo que describe el sistema actual. En el diseño conceptual (2.1) la Raspberry
  Pi se deja como historia, porque así se tomó la decisión; se agregó una tabla con el diseño frente a lo implementado.
- **Objetivos: sin cambios.** Alcances y limitaciones: ajustes pequeños para que no se contradigan entre sí.
- **El decisor de IA** se describe como es: un MLP de 15 entradas y una salida, entrenado con datos simulados etiquetados
  automáticamente, dentro de reglas de seguridad. Desaparece la versión vieja con evasión izquierda/derecha.
- **Nuevo 2.3**: escenarios, criterios de éxito, el porqué de cada número (Tabla N4) y la estadística.
- **Capítulo 3**: ya tiene los resultados de simulación verificados y las tablas vacías para el campo.
- **Recortes**: portadas de trabajos de grado, dos antecedentes débiles, 1.7.5 y 1.7.6 (repetían 1.6.1) y figuras de
  blogs. Ahorro: unas 5 páginas.
- **Código**: nada de código en el cuerpo; anexos A a F organizados por módulo.
- **Referencias**: Ahmed (duplicado) fuera, Kurunathan corregido a 2024, 13 referencias nuevas, 4 que no se citaban
  marcadas.

## 4. Cómo leer las cifras sin que el jurado te pille

Hay **tres experimentos distintos** en simulación. Nunca mezclar sus números en una misma frase.

| Experimento | Qué mide | Cifra principal |
|---|---|---|
| Protocolo del comité (1300 vuelos) | Si el sistema cumple los escenarios aprobados | 100 % de éxito con reglas y con IA |
| Discriminación (500 vuelos por decisor) | Si distingue a quien va a chocar de quien solo pasa cerca | IA + envolvente 94.0 % frente a reglas 91.2 % |
| Mundos de prueba (3840 vuelos) | Cómo se comporta en situaciones al azar, incluso imposibles | Personas a < 2 m: 218 frente a 420 |

**El 94 % contra el 91 %, en palabras simples.** En 500 vuelos con personas cerca de la trayectoria, las reglas aciertan
456 y la IA con envolvente 470. Como los dos sistemas enfrentan exactamente los mismos vuelos, la forma justa de
compararlos es mirar solo los vuelos en que no están de acuerdo: la IA acierta donde las reglas fallan 16 veces, y las
reglas aciertan donde la IA falla 2 veces. La prueba de McNemar dice que una diferencia de 16 a 2 casi nunca sale por
azar (p = 0.0013). Si alguien la calcula como si fueran muestras independientes, le dará p = 0.09; explícale que esa
prueba no aprovecha que los vuelos son los mismos.

**Lo que no se puede decir:**
- "La IA reduce los choques": 39 frente a 28 en 3840 vuelos **no es significativo** (p ≈ 0.18).
- "El sistema tiene 100 % de éxito en campo" con 10 de 10: el intervalo va de 72 % a 100 %.
- "La IA es más segura a la velocidad recomendada": a ≤ 4 m/s deja 24 riesgos frente a 22 de las reglas. Su ventaja ahí
  es la eficiencia (menos frenadas innecesarias).

**Lo que sí se puede decir:**
- En el protocolo del comité el sistema cumple el 100 % en simulación, sin choques y sin falsas activaciones.
- En los casos dudosos la IA dentro de reglas decide mejor que las reglas solas (94.0 % frente a 91.2 %, p = 0.0013) y
  frena sin necesidad menos veces (30 frente a 44).
- La IA permite detener al dron antes del tope de 8 m de las reglas: frente a una persona quieta la velocidad máxima
  segura sube de 4 a 12 m/s en simulación.

## 5. ¿Por qué IA y no solo condicionales? (la respuesta para el jurado)

1. Detectar personas en una imagen no se puede hacer con condicionales: por eso YOLO.
2. Decidir con medidas ruidosas sí se puede hacer con condicionales, pero hay que escoger entre frenar de más o frenar de
   menos. La distancia estimada con la caja de YOLO se equivoca hasta el doble de cerca, YOLO pierde cuadros y alguien que
   cruza se parece un instante a alguien que viene. El MLP mira las 15 medidas juntas y aprende la frontera con millones de
   ejemplos.
3. Las reglas siguen ahí como cinturón de seguridad: el LiDAR a menos de 3 m frena siempre, el árbitro decide cuándo se
   puede subir y la parada del operador manda sobre todo. La IA nunca puede saltarse eso.
4. El resultado medido: mejor discriminación y menos frenadas innecesarias, con la misma seguridad en el protocolo.

## 6. Los tres pasos para escribir Resultados y Conclusiones

**Paso 1 · Terminar lo físico y guardar los datos.** Con la sesión "Desarrollo Dron Parte Física", seguir
`docs/PLAN_MINIMO_FISICO.md` (pasos 1 a 7). En cada prueba guardar: el CSV de la Jetson, el log DataFlash de la Pixhawk,
fecha, hora, viento, sol o nubes, y fotos. Sin fotos no hay figuras.

**Paso 2 · Llenar el capítulo 3.**
- 3.4 (banco): cuadros por segundo sostenidos en 10 minutos, huecos del LiDAR, latencia riesgo → comando medida (meta:
  < 150 ms), retoma del piloto con el interruptor, y si el decisor en modo sombra decide igual que en simulación.
- 3.5 (campo): llenar la Tabla N8 (éxitos de 10, intervalo de Wilson, latencia, intervenciones del operador).
  Para el intervalo de Wilson se puede usar cualquier calculadora en línea o pedírselo a Claude.
- 3.6 (discusión): ¿la tasa de campo cae dentro del intervalo de la simulación? Si no, ¿por qué? (sensor, latencia,
  viento). Compararlo con lo que dicen los antecedentes (Vera-Yanez et al., 2023: pocos trabajos se prueban en vuelo
  real).

**Paso 3 · Escribir las conclusiones.** Un párrafo por objetivo específico, con la cifra que lo respalda, y uno general
que responda la pregunta de investigación de 1.3. Después ajustar el resumen y el abstract (máximo 250 palabras cada uno)
con los resultados.

## 7. Pendientes que son tuyos (los más importantes)

1. Preguntar al asesor si hay que avisar al comité el cambio de Raspberry Pi a Jetson Orin Nano.
2. Confirmar con la Facultad si las 100 páginas incluyen anexos y referencias.
3. Decidir si las Tablas 2, 3 y 4 pasan a un anexo (≈ 7 páginas menos).
4. Rehacer la Tabla 10 (hoy es una copia de la 9) y agregar la columna "Peso" a las Tablas 8 y 9.
5. Rehacer la Figura 18 (caja transparente) con la Jetson, la cámara USB y el buck de 12 V.
6. Confirmar los canales del radio (CH5, CH7, CH8) con la sesión física.
7. Buscar una fuente antropométrica para el alcance de pie y el salto (justifica los 3.30 m).
8. Completar las referencias incompletas (Avilés, León Mondragón, Bohórquez, OACI) y decidir qué hacer con Córdoba
   Velásquez y Ruiz Rincón (no se encontró en línea).
9. Confirmar si Tania sigue como coautora.
