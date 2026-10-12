# Progreso de la V16

Avance de las dos sesiones en la nube del plan `docs/PLAN_V16_REALISMO.md`. Cada fase deja una entrada: fecha, sesión,
qué se hizo, números medidos y qué sigue. Lo más reciente va abajo.

**Cómo se mide en la nube.** Los modelos `.zip` no están en Git, así que las mediciones usan la política de la V15 que sí
está en el repositorio (`simulacion/modelos/dron_politica.json`, 182 M pasos, la que va a la Jetson) **sin reentrenar**,
con `simulacion/herramientas/medir_v16.py` (partidas de 5 min de la misión V16). Sirve para comparar cada cambio con y
sin él; los números finales los dará el entrenamiento en el portátil.

---

## Fase A1 · Escenario y alturas (Sesión A, 2026-10-12)

**Qué se hizo** (`simulacion/entorno.py`, copia previa `entorno_v15b.py`):
- **Partida única**: misión completa con **2 paneles** de 4 a 6.5 m (2.6 m de alto), 0-2 civiles y el ladrón táctico
  (siempre el táctico: es el que tendrá posturas y salto). Es el "nivel" `NIVEL_V16 = 5`, fuera de los 5 niveles de la V15,
  que se conservan para comparar. Es el valor por defecto del entorno.
- **Civiles** que atraviesan la zona caminando tranquilos (1.1-1.5 m/s) de un borde al opuesto, rodeando los muros. Nacen
  a más de 9 m del dron. (Sus reacciones al ver el dron llegan en la fase A2.)
- **Alturas variables** (decisión 3): 2.5 m en el 360° de entrada, 3.0 m en tránsito y 2.0 m al inspeccionar detrás de un
  muro, **solo sin personas conocidas a menos de 8 m**. Con alguien cerca, nunca por debajo de **3.30 m** (D-043).
  "Conocida" es lo que el dron sabe: la persona que ve ahora, la que vio en los últimos 20 s y pudo seguir cerca, y el
  sospechoso designado mientras pudiera estar a menos de 8 m (corriendo a 2.5 m/s desde donde se lo vio por última vez).
- **Transiciones suaves**: la altura objetivo va en rampa (baja a 0.4 m/s, sube a 0.8 m/s y, con alguien cerca, sube a
  2.5 m/s como ArduPilot); nunca da un escalón.
- Arreglo del ladrón: con muros superpuestos, "cambiar de cubierta" elegía el mismo muro 2 de cada 3 veces; en la V16 va
  al otro muro.
- Herramientas nuevas: `herramientas/politica_json.py` (la política de la Jetson como referencia) y
  `herramientas/medir_v16.py` (medición rápida con `--set CONSTANTE=valor` para comparar con y sin un cambio).

**Hallazgo importante.** La primera versión bajaba a 2.0 m detrás del muro porque la nube de partículas ponía al ladrón
lejos; pero el ladrón táctico sigue la sombra del muro y estaba a 2-5 m sin que el dron lo viera: lo alcanzaba en 1 de
cada 2 partidas. Por eso, una vez designado el sospechoso, se lo considera "cerca" mientras pudiera haber llegado a menos
de 8 m. En la práctica las alturas bajas quedan para antes de encontrarlo (entrada, tránsito, inspección de la búsqueda
inicial) y para cuando está lejos de verdad.

**Números** (192 partidas de 5 min, política V15 sin reentrenar):

| | Con alturas variables | Sin ellas (siempre 3.30 m) |
|---|---:|---:|
| Custodia ≥ 60 s | 97.9 % | 97.4 % |
| Custodia ≥ 90 s | 79.7 % | 78.1 % |
| Rendición | 12.5 % | 7.3 % |
| Alcanzado por el ladrón | 0.5 % (1 partida) | 0 % |
| Perdido | 0 % | 1.0 % |
| Tiempo bajo 3.30 m | 1.5 % | 0.4 % |
| Bajo 3.30 m con una persona REAL a < 8 m (vista o no) | 0.5 % de ese tiempo | 0.02 % |

- Las alturas bajas no empeoran la custodia. En las corridas de depuración, los "alcanzados" que quedaron fueron antes
  de designar al sospechoso (360° de entrada a 2.5 m o verificando): el ladrón corrió hacia el dron sin que la cámara lo
  viera a tiempo. Es el riesgo que queda con lo que el dron no puede saber.
- La rendición es baja en la V16 (7-12 %) comparada con el nivel 4 de la V15 medido igual (44 %). No es un error: en esa
  medición el 30 % de los ladrones del nivel 4 era la "red del ladrón", que aquí se quedaba quieta. Con todos los ladrones
  activos el nivel 4 también baja a 20 %. La V16 usa siempre el ladrón táctico activo: es más difícil a propósito, y por
  eso la custodia es el número principal.

**Pruebas**: 6 nuevas en `tests/test_v16.py` (escenario, civiles, alturas con gente cerca, rampa, persona a 5 m durante el
360° de entrada). Total: 94 pruebas, todas pasan.

**Qué sigue**: fase A2 (posturas humanas en la física, salto con el brazo, civiles con reacciones).

---

## Fase A2 · Posturas humanas en la física (Sesión A, 2026-10-12)

**Qué se hizo** (`simulacion/entorno.py`):
- **Cuatro posturas que existen en la física**, no solo en el dibujo: de pie, agachado (~1.15 m), recostado de espalda
  contra la pared (a 0.45 m del eje del muro) y gateando (~0.6 m). Cada una cambia:
  - el alto del cuerpo (lo que tapa el muro, lo que toca el LiDAR, lo que tapa a otra persona);
  - el ancho de la caja de YOLO (agachado ×1.35, gateando ×1.8) y su confianza (agachado ×0.85, recostado ×0.95,
    gateando ×0.6);
  - la rapidez máxima (agachado ≤ 1 m/s, recostado quieto, gateando ≤ 0.65 m/s; cambiando de postura ≤ 0.3 m/s);
  - el alcance de la mano (el hombro baja con la postura).
- **Transiciones de 0.5 a 1 s** (pararse, agacharse, recostarse, tirarse al piso), con avance `pt` de 0 a 1.
- **El ladrón táctico elige la postura**: agachado al acercarse a su escondite, y al llegar se queda de pie, agachado o
  recostado contra la pared (20/45/35 %); a veces, en vez de asomarse, se corre **gateando** detrás del mismo muro hasta la
  otra mitad (modo `lm = 5`); para atacar se para ("sale y ataca").
- **Salto para agarrar el dron**: impulso (0.25 s quieto) → vuelo balístico (sube la altura del salto, 0.30-0.50 m, con
  velocidad horizontal hacia el dron) → aterrizaje y recuperación (0.6 s quieto) → recarga. La **mano** va del hombro hacia
  el dron con el largo del brazo (alcance de pie = 1.33 × estatura). **"Alcanzado" si la mano entra en el cilindro del dron**
  (radio 0.4 m, desde 0.15 m por debajo de su centro). A la altura segura ni el más alto (1.88 m) con el mejor salto llega.
- **Civiles con máquina de estados**: transitan; si notan el dron (a menos de 15 m y sin un muro en medio) reaccionan una vez
  por cruce: lo miran 5-20 s ("chismoseando"), lo graban con el celular, lo esquivan (a más de 5 m), se alejan 6-12 s o
  salen de la zona (desaparecen al llegar al borde). Todos rodean el dron desde 4.5 m: no pasan por debajo a propósito.

**Números** (192 partidas de 5 min, política V15 sin reentrenar):

| | A1 | A2 |
|---|---:|---:|
| Custodia ≥ 60 s | 97.9 % | 96.9 % |
| Custodia ≥ 90 s | 79.7 % | 80.2 % |
| Rendición | 12.5 % | 11.5 % |
| Alcanzado | 0.5 % | 0 % |
| Bajo 3.30 m con persona real a < 8 m | 0.5 % | 0.3 % |

- Tiempo del ladrón por postura: de pie 61.5 %, agachado 32.6 %, recostado 5.7 %, gateando 0.3 %. Saltos: 0.07 por partida
  (el dron casi siempre está a 3.30 m, donde no tiene sentido saltar).
- Civiles: transitan 78 %, miran el dron 8.6 %, lo graban 4.8 %, se alejan 3.8 %, salen 2.7 %, esquivan 2.2 %.

**Pruebas**: 9 nuevas (alto y duración de las transiciones, rapidez por postura, YOLO menos seguro agachado y gateando,
oclusión tras el muro por postura, el ladrón usa las 4 posturas, fases del salto, alcanza bajo y no a 3.30 m, reacciones de
los civiles, contrato `foto()`). `test_entorno.test_episodio_corto` ahora corre los 5 min del tope (con 2 paneles y 3.30 m
ninguna partida terminaba en 150 s). Total: 103 pruebas, todas pasan.

### Contrato `foto()` para el visor (Sesión B)

Cada cuadro de una repetición es el diccionario que devuelve `EntornoDronPersona.foto(i)`. Se conservan todos los campos
de la V15; estos son los **nuevos de la V16** (los ángulos en radianes, antihorario desde +X, como `d[3]`; distancias en m):

**En cada persona** (`pers[k]`; la primera es siempre el ladrón; los civiles que salen de la zona desaparecen de la lista,
así que hay que seguirlos por `id`):

| Campo | Qué es |
|---|---|
| `pos` | Postura (destino de la transición): 0 de pie, 1 agachado, 2 recostado contra la pared, 3 gateando |
| `pos0` | Postura de la que viene |
| `pt` | Avance de la transición, 0 a 1 (1 = terminada). Mezclar las animaciones `pos0` → `pos` con `pt` |
| `alto` | Alto actual del cuerpo (m), ya con la postura y la transición |
| `mira` | Hacia dónde mira (rad). Recostado: de espaldas a la pared. Mirando o grabando: hacia el dron |
| `civ` | Estado del civil (`null` en el ladrón): 0 transita, 1 mira el dron, 2 lo esquiva, 3 se aleja, 4 sale de la zona, 5 graba con el celular |
| `graba` | `true` si está grabando con el celular (solo animación) |

**En el cuadro**:

| Campo | Qué es |
|---|---|
| `v16` | `true` si la partida es la misión V16 de 2 paneles |
| `salto` | `{"f": fase, "h": altura de los pies sobre el piso, "mano": [x, y, z]}` del ladrón. Fases: 0 no salta, 1 impulso (se agacha y empuja, 0.25 s), 2 en el aire, 3 aterriza y se recupera (0.6 s). La mano está siempre (brazo hacia el dron); en el salto, el brazo va extendido hacia el dron |
| `alt_obj` | Altura objetivo del dron (m), la que se le pide a la Pixhawk (va en rampa) |
| `g8` | `true` si el dron sabe de alguien a menos de 8 m (por eso no baja de 3.30 m) |
| `cam_piso` | Detecciones de la cámara al piso (lista; se llena en la fase A3, abajo se documenta su forma) |

Además: `lm = 5` en el ladrón es "se corre gateando detrás del muro". `sz` (V15) sigue siendo la altura del salto.

**Qué sigue**: fase A3 (cámara al piso, TF03 al chasis y TF-Luna en el gimbal, desenfoque por movimiento, gimbal BaseCam o
servo, ruido de GPS y barómetro).

---

## Fase A3 · Sensores (Sesión A, 2026-10-12)

**Qué se hizo** (`simulacion/entorno.py` y `simulacion/control.py`, copia previa `control_v15.py`). Todo solo en la misión
V16: las partidas de la V15 quedan iguales.
- **Cámara al piso** (decisión 2): IMX219 de 62.2° × 48.8°, **fija al chasis y recta hacia abajo** (`CAM_PISO_HFOV`,
  `CAM_PISO_VFOV`, `CAM_PISO_PITCH`); se inclina con el cabeceo y el alabeo. Mismo ruido, pérdidas y retardo que la
  principal. Si ve a la persona seguida (debajo del dron), el tracker no la suelta y el Kalman se corrige con su posición:
  el reflejo de punto ciego sabe dónde está. **No cuenta como "a la vista"** para la custodia ni la recompensa (eso sigue
  siendo la cámara principal). La red recibe 3 entradas nuevas (la ve, adelante, izquierda): `OBS_DRON` pasa de 192 a 195.
- **LiDAR según la sección 6**: el **TF03 va fijo al chasis** mirando al frente (+1°): frena y mapea; los impactos en el
  suelo se descartan con la actitud de la Pixhawk (d < h / sin(cabeceo hacia abajo) − 0.4 m). El **TF-Luna va en el gimbal**:
  mide la distancia a la persona centrada y agrega muros cercanos al mapa; su alcance es de 3 a 8 m según la partida.
  - Consecuencia medida: con el TF03 casi horizontal, el 360° de entrada a 2.5 m solo mapeaba 38-50 % de los muros a más de
    10 m (el rayo pasa por encima de 2.6 m). **A 2.0 m los mapea todos hasta 25 m**: la entrada quedó a 2.0 m (dentro de la
    decisión 3). A 3.30 m el TF03 pasa por encima de los muros (el dron también): ahí mapea el TF-Luna (< 8 m).
- **Desenfoque por movimiento**: exposición de 4 ms; el cuerpo se corre en la imagen por la guiñada, el movimiento del gimbal
  y el de la persona; YOLO pierde confianza como 1 / (1 + (px / 12)²). A 120°/s de guiñada se detecta claramente menos.
- **Tipo de gimbal** (`GIMBAL_TIPO`): "basecam", "servo" o **"mixto"** (cada partida uno, al azar: aleatorización del
  dominio). El servo MG90D: retardo de la Pixhawk de 50-100 ms, ~600°/s, zona muerta de 1°, topes mecánicos −45°/+15°. Prueba
  nueva de regla dura: el servo tampoco pasa de −45° con comandos extremos y el chasis cabeceando.
- **Ruido de navegación**: deriva del GPS/EKF de 0.5-1.5 m (cambia lento, ~30 s) y error del barómetro de ±0.3-0.5 m (~20 s).
  El mundo que el dron recuerda (mapa, última posición, nube, rutas) queda en el marco que él creía y se desalinea al
  derivar; la geocerca de ArduPilot usa la posición estimada (margen de 3 m). La Pixhawk sostiene la altura que **ella
  cree**.
- **Dos errores corregidos de la lógica de identidad** (aparecieron al cambiar el azar; la prueba de regla dura "humano en
  el lazo" los detectó y **no se relajó**):
  1. Cuando el operador respondía "no es él", en ese mismo cuadro la interrupción táctica usaba la detección vieja (la del
     civil) y lo volvía a fijar. Ahora un "no es él" no puede interrumpir con esa detección.
  2. Tras el clic del operador, el tracker queda amarrado 1 s a la persona que él señaló (no salta aunque sigan
     superpuestas).
- Después de un esquive (enfriamiento de 1 s), si quedó bajo la altura segura, el dron sigue subiendo.

**Números** (192 partidas de 5 min, política V15 sin reentrenar; ±2-3 % de ruido entre corridas):

| Variante | Custodia ≥ 60 s | ≥ 90 s | Rendición | Alcanzado | Altura REAL < 3.0 m con persona a < 8 m | Saltos / partida |
|---|---:|---:|---:|---:|---:|---:|
| A2 (sin los sensores nuevos) | 96.9 % | 80.2 % | 11.5 % | 0 % | — | 0.07 |
| **A3 completa** (gimbal mixto, desenfoque, GPS y barómetro) | 88.5 % | 60.4 % | 6.8 % | 1.0 % | 1.65 % | 0.27 |
| A3 solo BaseCam | 91.1 % | 64.6 % | 6.8 % | 0 % | 2.2 % | 0.32 |
| A3 solo servo | 91.1 % | 65.6 % | 7.8 % | 0 % | 2.1 % | 0.28 |
| A3 sin desenfoque | 92.2 % | 68.2 % | 7.8 % | 0 % | 1.8 % | 0.28 |
| A3 sin ruido de navegación | 97.4 % | 77.1 % | 8.3 % | 0 % | 0.2 % | 0.08 |
| A3 solo deriva del GPS | 94.3 % | 75.5 % | 7.8 % | 0 % | 0.2 % | 0.07 |
| A3 solo barómetro | 88.5 % | 72.9 % | 6.2 % | 0.5 % | 2.7 % | 0.29 |
| A3 con **TF-Luna como altímetro** | 91.7 % | 76.0 % | 9.4 % | 0.5 % | 0.25 % | 0.08 |

- La cámara al piso ve al objetivo ~3.5 % del tiempo (cuando queda debajo o muy cerca).
- **Lo que más pesa es el barómetro**: la Pixhawk cree estar a 3.30 m y en la realidad puede estar a 2.9-3.1 m, dentro del
  salto del ladrón (2.6-3.0 m): los saltos se triplican y la altura real queda bajo 3.0 m con alguien cerca el 2.7 % del
  tiempo. La deriva del GPS baja la custodia unos 3 puntos (el mapa recordado se desalinea). El desenfoque y el tipo de gimbal
  pesan poco con esta política; su papel es darle a la red, al entrenar, un motivo físico para moverse suave.

**Decisión abierta para Brahian (no cambia una regla dura).** La altura segura de 3.30 m (D-043) tiene 0.3 m de margen sobre
el salto; el error del barómetro (±0.3-0.5 m) se lo come. Opciones: (a) dejarlo así (riesgo medido arriba); (b) **un TF-Luna
mirando al piso como altímetro** (la alternativa de la sección 6 del plan: ArduPilot lo usa como telémetro y el error baja a
~5 cm; en la simulación devuelve la altura real bajo 3.0 m a 0.25 %); (c) subir la altura segura que se le pide a la Pixhawk
en ~0.5 m. La simulación queda con el barómetro (`ALTIMETRO = "baro"`, el hardware de hoy); cambiar a `"luna"` es una línea.

**Contrato `foto()` — campos de la A3** (además de los de la A2):

| Campo | Qué es |
|---|---|
| `cam_piso` | Lista de detecciones de la cámara al piso: `{"id": ID de la persona, "p": [x, y] posición medida en el piso, "obj": true si es la persona seguida}`. Vacía si no ve a nadie |
| `servo` | `true` si en esta partida el gimbal es el servo MG90D (si no, la BaseCam) |
| `luna` | Punto `[x, y, z]` que mide el TF-Luna (lo que la cámara centra). `lh` (V15) es ahora el punto del TF03 del chasis |
| `dz_est` | Altura que cree la Pixhawk (con el error del barómetro); `d[2]` es la real |
| `e_gps` | Deriva del GPS en ese momento `[ex, ey]` (m) |

**Pruebas**: 9 nuevas (TF03 al chasis: ve el muro a 2.0 m, pasa por encima a 3.30 m y descarta el suelo cabeceando; TF-Luna
solo dentro de su alcance; cámara al piso ve debajo y no a 6 m, e inclinada ve adelante; el desenfoque baja la detección;
gimbal mixto; la deriva corre el mapa recordado; la V15 sin ruido; regla dura del servo). `test_entorno` acepta la política
de la V15 que está en Git (192 entradas) hasta que se entrene la V16. Total: 111 pruebas, todas pasan.

**Nota para la Jetson**: la política V16 tendrá 195 entradas (las 3 de la cámara al piso al final). El
`modelos/dron_politica.json` que está en Git sigue siendo el de la V15 (192) hasta que se entrene la V16.

**Qué sigue**: fase A4 (recompensa: custodia principal, rendición como bono, suavidad y abordaje con conciencia de coberturas).
