# Plan V15 · Currículo por niveles, predicción y física del ladrón

Plan del arquitecto (2026-10-10, revisión 3: **aprobado por Brahian**), hecho a partir de sus ideas por voz y del
análisis del código de la V14. Lo implementa la sesión "Simulacion" por fases, con pruebas, midiendo con el modelo
actual antes de entrenar.

---

## 1. Dónde estamos (V14, medido hoy)

- El entrenamiento V14 **está corriendo** (lanzado 12:36). A los 4.2 M pasos ya pasó el nivel 0 (95 % de éxito a los
  2.0 M) y el nivel 1 (92 % a los 4.1 M); va en el nivel 2 "Ruido visual". Subió tan rápido porque arrancó de un
  modelo con 770 M pasos: **los niveles actuales le quedan fáciles y no enseñan nada nuevo.** Se deja correr (D4).
- Niveles de la V14: 0 Duelo abierto (huida en zigzag + 30 % "cenit"), 1 Muro único, 2 Muro + civil que cruza la
  línea de vista, 3 Misión completa (zona). El despegue y el tránsito (fase 1) solo existen en `mision.py`, para el
  visor; no se entrenan.
- El duelo de **cenit** (el ladrón se mete debajo del dron) da **0 %** y hoy se excluye del criterio para subir.
- La misión se cumple con **30 s de rastreo ACUMULADO** (`t_fijado` solo se reinicia en el lock-on; perderlo no
  borra lo que ya llevaba).

Huecos que encontré en el código y que hacen que lo pedido **no se pueda aprender todavía**:

| Hueco | Dónde | Consecuencia |
|---|---|---|
| La predicción es una velocidad promediada (EMA 0.75/0.25) y una recta de 2 s | `entorno.py` (PREDECIR, `tvx/tvy`) | No predice curvas, frenazos ni "se metió debajo de mí"; no sabe "dónde puede estar" detrás de un muro |
| El tracker **nunca confunde personas** | no hay modelo de cambio de ID | El nivel con civil no prueba la identidad: solo prueba la oclusión |
| El LiDAR llega a **20 m** y lanza **1 rayo cada 0.1 s** | `LIDAR_MAX`, `_lidar_camara` | El TF03 real llega a 30+ m y mide a 100 Hz (10 rayos por paso). Girando a 90°/s el simulador deja 9° entre puntos: un muro de 5 m a 25 m recibe 1-2 impactos y no se detecta (`K_DET = 4`) |
| El giro de 360° va a 3.0 m con la cámara a −15° | `Z_GIRO`, `GIMBAL_GIRO` (D-027 abierta) | El rayo pega en el suelo a 11.2 m: **solo mapea muros a menos de 11 m** |
| "Stamina" = 2 s de sprint que se recarga | `STAMINA_MAX` | No hay cansancio acumulado: el ladrón corre igual en el segundo 200 que en el 5 |
| Distancia de seguimiento 3.5-5 m | `R_OPT_MIN/MAX` | Contra un ladrón que carga a 3.4 m/s el dron pierde ~3.3 m antes de igualarle la velocidad (jerk 5 m/s³); con el punto ciego de 1.7 m a 3 m de altura, a menos de ~5 m siempre se le mete debajo. Por eso "cenit" y "debajo" dan 0 % |
| La búsqueda tras un muro solo sabe flanquear | FLANQUEO_PROFUNDO | Si el ladrón cambia de lado, el dron le da vueltas al muro (el "gato y ratón") |
| Éxito por tiempo acumulado | `t_fijado`, `T_RASTREO` | Verlo a ratos cuenta igual que no soltarlo nunca |

## 2. Cuándo se cumple la misión (pedido de Brahian)

**No hay un tiempo fijo de refuerzos.** La misión se cumple cuando **el ladrón se rinde**, y solo se rinde si el dron
lo mantiene a la vista **sin interrupción**:

- **Contador continuo:** cuenta el tiempo seguido con el ladrón fijado y a la vista. Si lo pierde **de verdad**,
  **vuelve a cero**; lo que llevaba antes no vale.
  - **Se reinicia** solo cuando el dron "ya no sabe dónde está": cuando sale de PÉRDIDA (la predicción no lo
    re-encontró) y entra a la búsqueda (FLANQUEO_PROFUNDO, GIRO_360, SIGUIENTE_OBSTÁCULO, ALTURA_TÁCTICA).
  - **Se pausa** (no suma, pero no se borra) mientras no lo ve y todavía sabe dónde está: parpadeos, un civil que pasa
    por delante, medio se salió del cuadro y volvió, memoria del tracker (1 s) o la persecución predictiva (PÉRDIDA).
- **Rendición:** el ladrón se rinde cuando el contador continuo llega a
  **T_rinde = 20 s + 100 s × reserva** (reserva de energía del ladrón, de 1 = fresco a 0 = agotado; sección 4B).
  - Fresco: necesita 2 minutos seguidos sin poder esconderse. Agotado: 20 s.
  - Así se juntan las dos ideas de Brahian: se rinde porque se cansó **o** porque el dron es tan bueno que no lo deja
    esconderse nunca.
  - Al rendirse se queda quieto (en el visor: "SE RINDE").
- **Tope de la partida:** 5 minutos (`PASOS_EPISODIO` 240 s → 300 s). Si se acaba el tiempo y el ladrón no se rindió,
  **pierde el dron** (gana el ladrón en la competencia), aunque todavía lo esté viendo. Otras fallas: perderlo del todo
  (90 s de búsqueda sin éxito), que lo alcance, choques y geocerca.
- El ladrón **arranca con el pulso alto** por la tensión (≈ 100-110 en vez de 70) y la reserva llena o casi llena.
  Hay que calibrar para que un dron bueno sí logre la rendición dentro de los 5 minutos (con la fórmula, 2 minutos
  seguidos sin dejarlo esconderse bastan aunque esté fresco).
- Recompensa: `R_EXITO` al rendirse; `R_VISTA` y `R_PIERDE` como hoy. El reinicio del contador ya es el castigo por
  soltarlo (retrasa la victoria). Se ajusta midiendo.

## 3. Currículo: 5 niveles (aprobado, D1)

Orden: duelo solo → identidad con un civil → muro → muro + civil → misión completa. **El entrenamiento V15 arranca
en el nivel 0 y corre cada nivel de verdad**, aunque el modelo ya lo domine: Brahian quiere ver en el visor cómo
aprende cada nivel (sección 5).

| Nivel | Escenario | Qué aprende el dron | Qué hace el ladrón | Para subir (1000 partidas del nivel) |
|---|---|---|---|---|
| **0 · Duelo abierto** | Dron en el aire con el objetivo ya fijado. Sin muros ni civiles | Mantenerlo en el campo de visión; **predecir** hacia dónde se va y rotar antes; **no dejar que se le meta debajo** (prioridad) | Huye en zigzag, cambia de rumbo en seco y busca el punto ciego (debajo). **No ataca** en este nivel | Rendición ≥ 85 % **contando las partidas de cenit** (ya no se excluyen) y cenit ≥ 70 % por separado |
| **1 · Duelo con civil** | Nivel 0 + un civil que se cruza (pasa por delante, se superpone en la imagen, a veces cerca del dron) | **No cambiar de persona**: sostener el ID, reportar al operador y pedir reconfirmación si hay duda; esquivar al civil sin perder al ladrón | Igual que en 0; aprovecha al civil para cruzarse con él | Rendición ≥ 85 %, ID correcto ≥ 98 % del tiempo, **0 cambios de ID sin detectar**, 0 choques |
| **2 · Muro** | Dron en el aire + 1 muro + ladrón | Giro de 360° que mapea el muro; si se esconde: la secuencia de la sección 4F; perseguir y no soltarlo | Se esconde detrás apenas el dron pasa al otro lado, se asoma, cambia de lado, ataca si lo acorralan; **se cansa** | Rendición ≥ 80 % y re-adquisición media < 8 s |
| **3 · Muro y civil** | Nivel 2 + civil que se cruza para hacerle perder el objetivo | Todo lo anterior junto | Igual que 2, usando al civil como pantalla | Rendición ≥ 75 % e ID correcto ≥ 98 % |
| **4 · Misión completa** | Despegue desde la plataforma, tránsito con obstáculos (piloto + bloqueo frontal), entrada a la zona, **varios muros** (3-4), civiles | El 360° de entrada que alcanza **todos** los muros; buscar muro por muro según la probabilidad; todo lo anterior | Táctico, con cansancio; en una fracción, la política aprendida | Nivel final: solo se reporta |

- Se mantienen el mínimo de 2 M pasos por nivel, la paciencia de 50 M y el 25 % de repaso de niveles anteriores.
- **Fase 1 (tránsito) no se entrena:** por alcance del proyecto (D-009) la vuela el piloto con el bloqueo frontal.
  En el nivel 4 la red arranca al entrar a la zona, como en `mision.py`. El visor sí muestra el despegue.
- Con 3-4 muros el ladrón aprendido (`ladron_congelado.pt`, que espera 2 paneles) no sirve tal cual: en el nivel 4
  usar el táctico o pasarle los 2 muros más cercanos.

## 4. Cambios transversales (física, sensores y lógica)

### A. Predicción de verdad: filtro de Kalman + "nube de probabilidad"
Es lo que Brahian más pidió ("si se fue hacia abajo, saber que se está metiendo debajo; si lleva una trayectoria,
rotar hacia esa trayectoria").

1. **Con el ladrón a la vista: filtro de Kalman** sobre su posición en el suelo (bbox de YOLO + ángulos del gimbal +
   LiDAR cuando lo toca), modelo de velocidad y aceleración (o de giro coordinado). Da velocidad, aceleración, rumbo
   de giro y **cuánta incertidumbre** hay. Reemplaza el EMA de `tvx/tvy`.
2. **Sin verlo: filtro de partículas** (≈ 200 hipótesis de "dónde puede estar"). Cada partícula se mueve con la
   cinemática humana que ya tiene el simulador (no atraviesa muros, no gira en seco, se cansa). Cada cuadro, **las
   partículas que la cámara está viendo y donde no hay nadie se borran** ("información negativa"). Lo que sobrevive
   es exactamente "detrás del muro", "debajo de mí" o "siguió por allá".
3. La búsqueda determinista usa la nube: rota hacia donde está la mayor masa de probabilidad que hoy no se ve, y
   elige el muro a revisar por probabilidad (no solo por cercanía). También dice **de qué lado del muro se proyecta**
   que se escondió (sección 4F).
4. **Reflejo anti-cenit predictivo** (refuerzo pedido para el nivel 0): si la nube o el Kalman dicen que va a pasar
   por debajo, el dron gira la nariz hacia el **punto de salida** previsto (a 120°/s, 180° tardan 1.5 s; cruzar el
   punto ciego le toma al ladrón ~1.5 s) y, si se queda debajo, se aparta y vuelve a mirar.
5. **Distancia de seguimiento adaptativa:** cuando el ladrón se acerca a más de ~1 m/s, la distancia mínima sube de
   3.5 m a ≈ radio ciego + distancia que se cierra antes de igualarle la velocidad ≈ **6 m**.

No cambia el tamaño de las observaciones: la predicción y la memoria espacial que ya entran a la red (las columnas de
"dónde estaría ahora") se llenan con el Kalman o la nube. En la Jetson, 200 partículas a 10 Hz son despreciables.
En el visor: la nube dibujada en el piso y en el minimapa SLAM.

### B. Cansancio del ladrón (velocidad crítica + reserva + pulso)
Modelo estándar de fisiología del ejercicio (velocidad crítica de Monod y Scherrer; balance W′ de Skiba et al. 2012):

- **Velocidad crítica (VC)** ≈ 3.0 m/s: por debajo puede correr mucho rato.
- **Reserva (D′)** ≈ 150 m: lo que corra **por encima** de VC la gasta; por debajo se recupera despacio. La
  "reserva" de la sección 2 es D′ restante / D′ total (de 1 a 0).
- Con la reserva baja: no puede esprintar, se esconde más tiempo, ataca menos. Sin reserva: solo trota o camina.
- **Cuerpo de una persona colombiana** (pedido de Brahian): estatura media de los hombres ≈ 1.72 m (NCD-RisC 2019:
  171.9 cm; cédulas, nacidos 1980-84: 170.6 cm). Cada partida sortea la estatura del ladrón y de los civiles
  (≈ N(1.72, 0.07) m, entre 1.58 y 1.88). De ahí salen: alcance de pie ≈ 1.33 × estatura (≈ 2.29 m), salto de
  0.30-0.50 m (adulto no entrenado) → alcance saltando ≈ 2.6-2.9 m, ancho de hombros ≈ 0.45 m. Hoy el simulador usa
  1.70 m, alcance 2.2 m y salto 2.5-2.7 m: casi igual, pero fijo. **La altura segura del dron** (giros de búsqueda,
  flanqueo, `Z_ATAQUE`) debe salir del alcance saltando más alto (percentil 99) + 0.3 m; si pasa de 3.0 m, se sube.
- **Bogotá (para después, no ahora):** a 2 640 m el aire es ~22 % menos denso (las hélices dan menos empuje: menos
  aceleración y más consumo de batería) y la capacidad aeróbica de la gente es algo menor aunque esté aclimatada. Se
  anota para la validación con el dron real; el clima no entra en la V15.
- **Pulso** (visor y narrativa): reposo 70, +30 por el estrés de estar huyendo, sube con la velocidad y con la
  reserva gastada, máximo ~190, con retardo de 20-40 s.
- **El dron no observa el pulso ni la reserva** (no hay sensor para eso en el dron real). Solo ve que va más lento.
- Los valores iniciales se ajustan con la literatura de adultos no entrenados y se documentan para Tania.

### C. LiDAR TF03 con sus números reales
Datasheet de Benewake: TF03-100 = 100 m (reflectividad 90 %), **30 m con objetivo oscuro (10 %) a pleno sol
(100 klux)**; TF03-180 = 180 m / 50 m en esas condiciones. Haz de 0.5°, ±10 cm hasta 10 m, 100 Hz por defecto
(hasta 1000 Hz).

- `LIDAR_MAX` de 20 → **30 m** (peor caso del modelo de 100 m; vale para los dos).
- **10 rayos por paso de 0.1 s** (100 Hz reales), repartidos en el giro de ese paso, al menos durante el 360°.

### D. El giro de 360° que alcanza todos los muros
El rayo va pegado a la cámara. Desde la altura h con la cámara a −α, el rayo toca un muro de 2.6 m solo entre
d_min = (h − 2.6)/tan α y d_max = h/tan α (ahí toca el suelo). Calculado:

| Altura | Cámara | Muros que mapea | Ve una cabeza desde |
|---|---|---|---|
| 3.0 m | −15° (hoy) | 1.5 – 11.2 m | 2.3 m |
| 3.0 m | −8° | 2.8 – 21.3 m | 3.1 m |
| 3.0 m | **−6°** | **3.8 – 28.5 m** | 3.4 m |
| 3.0 m | 0° | ninguno (pasa por encima de 2.6 m) | 4.9 m |
| 2.5 m | 0° | 0 – 30 m | 3.0 m (pero dentro del salto del ladrón) |
| **2.5 m** | **−3°** | **0 – 30 m** (el suelo a 47.7 m) | 2.5 m |

**Decisión D5 (idea de Brahian, cierra D-027): dos tipos de 360°.**

1. **360° de entrada (el primero, al llegar a la zona): BAJO, a 2.5 m con la cámara a −3°, una sola vuelta.** Mapea
   todos los muros de 0 a 30 m en 4 s y ve cabezas desde 2.5 m. Es seguro porque en ese momento el ladrón está lejos
   (aparece a 8-20 m) y casi nunca ha notado al dron. **Guarda:** si alguien entra a menos de 6 m o se acerca rápido,
   el dron sube de inmediato a la altura segura (el reflejo del árbitro ya existe) y termina la vuelta arriba.
   (El 48 % de "alcanzado" de la D-027 a 2.5 m fue con TODOS los 360° bajos, incluidos los de búsqueda con el ladrón
   alerta y cerca; aquí solo el primero es bajo.)
2. **360° de búsqueda (los siguientes, con el ladrón alerta): ALTO**, a la altura segura (≥ 3.0 m, sección 4B), una
   vuelta con la cámara a **−8°** (muros de 2.8 a 21 m para actualizar el mapa; cabezas desde 3.1 m). El mapa grande
   ya lo hizo la vuelta de entrada. En la fase A se compara contra −15° (lo de hoy) y se deja el mejor.

El giro empieza siempre hacia el lado del muro / donde se proyectó al ladrón, nunca al contrario (hoy `busca_dir` ya
lo hace con el producto cruz; agregar una prueba que lo garantice).

### E. Identidad: modelo de cambio de ID y confirmación al operador
- Cuando el ladrón y otra persona se superponen en la imagen, el tracker puede **cambiarse de persona** con una
  probabilidad que baja si se mueven distinto (Kalman) y si la apariencia los distingue (ReID; peor de lejos).
- El dron detecta la duda (salto en la predicción del Kalman o caída de la similitud de apariencia) → estado
  **RECONFIRMAR**: mantiene a los dos en cuadro y pide al operador un clic (el operador simulado responde en 1-2 s).
- Estado continuo hacia la estación de tierra: "SIGUIENDO ID 17 · confianza 0.93" / "¿SIGUE SIENDO ÉL?".
- Métricas nuevas: % del tiempo con la persona correcta, cambios de ID detectados / sin detectar, reconfirmaciones.
- Respeta la regla 4 (humano en el lazo): ante la duda decide el operador, nunca la IA.

### F. Secuencia tras el muro (D2, decidida por Brahian; búsqueda determinista, regla 3 intacta)
Cuando el ladrón se esconde detrás de un muro, en este orden (en cualquier paso, apenas lo ve → PERSECUCIÓN, con la
interrupción táctica de la V13):

1. **Detrás del muro por el lado por donde se escondió:** la nube/Kalman dice por qué punta se metió; el dron va
   detrás del muro por ese lado (lo que ya hace FLANQUEO_PROFUNDO, ahora guiado por la predicción), busca ahí y gira
   **hacia ese lado** (nunca al contrario).
2. **Si no está → al otro extremo del muro** y mirar detrás desde ahí (el ladrón pudo rodear hacia la otra punta).
3. **Si no está → MIRAR EL MURO DE CANTO ("el palito"):** el dron se para **en la prolongación del muro**, más allá de
   una punta, mirando a lo largo del muro. De canto, el muro es un palito delgado y el dron **ve las dos caras a la
   vez** en todo su largo. Hace **un solo barrido: una vez a la izquierda y una vez a la derecha** (±20° aprox.) y
   ya; no hace falta más, porque pegado al muro el ladrón ya no tiene dónde esconderse.
   - Distancia desde la punta: para cubrir 2 m a cada lado del muro (la zona oculta de 1.6 m + el cuerpo),
     a = 2.0 / tan(38.9°/2 − 1°) = **6.0 m**. La otra punta queda a 10 m (muro de 4 m) o 12.5 m (muro de 6.5 m).
   - Altura segura (≥ 3.0 m) y cámara a ≈ −14° (encuadra el torso entre 6 y 12.5 m).
   - Punta elegida: la que quede dentro de la arena y con la ruta libre (raycasting contra la nube); de preferencia
     la más cercana al dron después del paso 2.
   - **Si el ladrón se esconde justo detrás de la punta lejana, en la línea del muro:** el ladrón es más ancho
     (hombros ≈ 0.45 m) que el muro (≈ 0.2 m). Para que el simulador lo sepa: muros con **grosor** (0.2 m) y
     detección por **ancho** del cuerpo (hecho en la fase A).
   - **Corrección por perspectiva (hallazgo de la fase A, verificado por el arquitecto):** la punta CERCANA, por estar
     más cerca, tapa más de lo que parece: desde 6 m de canto exacto se ve solo el 7 % (muro de 6.5 m) a 24 % (muro
     de 4 m) del ancho de los hombros. Alejarse ayuda poco (a 10 m: 26-37 %; a 14 m: 35-42 %, con el ladrón ya muy
     lejos) y subir no ayuda (la visual tiene que pasar por encima de todo el muro). Lo que sí sirve es que **el
     "izquierda-derecha" sea un desplazamiento lateral** (no solo un giro): corrido 0.5-1.5 m al costado, a 6 m,
     se ve el 30-37 % para muros de 4 y 6.5 m. Mientras está corrido a un lado no ve la cara contraria (0 %), por
     eso el orden es: **centrado de canto (ve las dos caras) → ~1 m a un lado → ~1 m al otro lado**, con la nariz
     apuntando a lo largo del muro; primero hacia el lado que diga la predicción.
4. **Si tampoco está → se fue corriendo hacia otro lado → 360° de búsqueda (alto)** y después lo de hoy: siguiente
   obstáculo, altura táctica, hasta MISIÓN_PERDIDA (90 s).

### G. Detección parcial probabilística
Hoy basta el 15 % del cuerpo visible (umbral fijo). Proponer que la probabilidad de detección suba con la fracción
visible y baje con la distancia, y calibrarla luego con la Jetson (persona medio tapada por una puerta).

## 5. Visor: una pestaña por nivel, con su iteración

El selector "Repetición a mostrar" (arriba a la derecha de `index.html`) hoy tiene "Misión completa · en vivo" y
"Partida en zona · en vivo". Queda así:

- Nivel 0 · Duelo abierto · en vivo (it N)
- Nivel 1 · Duelo con civil · en vivo (it N)
- Nivel 2 · Muro · en vivo (it N)
- Nivel 3 · Muro y civil · en vivo (it N)
- Nivel 4 · Misión en zona · en vivo (it N)
- Misión completa (despegue) · en vivo (it N)
- Hitos agrupados por nivel: "Nivel 0 · it 5", "Nivel 0 · it 10", … (quedan guardados aunque el nivel ya se haya
  superado, para ver cómo fue aprendiendo).

Reglas de grabación:
- La repetición de cada nivel se graba con la política actual **forzada a ese nivel** (`replay_nivel_K.json`) e
  indica la iteración. Los niveles que el entrenamiento aún no alcanza se marcan "aún no entrenado".
- **Mientras el entrenamiento está en un nivel, se guarda un hito de ese nivel cada 5 iteraciones durante sus
  primeras 50** (así se ve el aprendizaje aunque el nivel pase rápido) y luego cada 20.
- Para no frenar el entrenamiento: cada 5 iteraciones el nivel actual y la misión; los demás niveles, uno por turno.
- Paneles: pulso y reserva del ladrón, contador continuo y "SE RINDE", confianza del ID / alerta de reconfirmación,
  la nube de probabilidad y el punto de vigilancia de perfil.
- Regla de siempre: no cambiar el diseño del visor; solo agregar dentro de los paneles existentes.

## 6. Lo que NO cambia

- Reglas duras de `CLAUDE.md`: gimbal −45°..+15°, geocerca, búsqueda determinista (la secuencia de 4F es
  determinista), humano en el lazo, árbitro de seguridad, la red no estabiliza.
- Observaciones (192) y acciones (10): misma red, se sigue afinando desde el último checkpoint de la V14.

## 7. Fases de implementación (cada una: pruebas + medición con el modelo actual sin reentrenar)

| Fase | Contenido | Se acepta si |
|---|---|---|
| A · Sensores y mundo | LiDAR 30 m y 10 rayos/paso; 360° de entrada bajo y de búsqueda alto; cansancio + pulso; cuerpo colombiano y altura segura; muros con grosor; detección parcial probabilística por alto y ancho | El 360° de entrada mapea muros a 25 m; pruebas pasan; pasos/s no caen más de 30 % |
| B · Predicción | Kalman + nube de partículas; búsqueda guiada por la nube; reflejo anti-cenit; distancia adaptativa | Escenario "cenit/debajo" > 0 % (meta 70 %); "cambio brusco" se mantiene en 100 % |
| C · Identidad | Cambio de ID, estado RECONFIRMAR, operador, métricas | 0 cambios sin detectar en 1000 partidas del nivel 1 |
| D · Muro | Secuencia: lado proyectado → otro extremo → muro de canto (izquierda-derecha) → 360°; prueba del sentido de giro; escenario fijo nuevo "detrás de la punta" | "Tras muro" ≥ la de hoy, menos tiempo de re-adquisición, y el ladrón detrás de la punta se detecta |
| E · Éxito, currículo y visor | Contador continuo (pausa/reinicio) y rendición; tope 5 min = pierde el dron; 5 niveles con sus criterios (cenit cuenta); ataques desde el nivel 2; pestañas por nivel con iteración e hitos densos | Las 6 pestañas cargan; el nivel se guarda y se retoma |

Al final: lanzar la V15 desde el último checkpoint de la V14, **empezando en el nivel 0**.

## 8. Decisiones

| | Decisión | Estado |
|---|---|---|
| D1 | 5 niveles en ese orden; correr cada uno desde el 0 y verlos en el visor; el cenit cuenta para subir del nivel 0 | **Aprobada** (Brahian) |
| D2 | Tras el muro: lado por donde se escondió → otro extremo → muro de canto con un barrido izquierda-derecha → 360° | **Aprobada** (Brahian, determinista) |
| D3 | Éxito = el ladrón se rinde; T_rinde = 20 s + 100 s × reserva; contador continuo que se pausa en los parpadeos y se reinicia al pasar a búsqueda; tope de 5 min sin rendición = pierde el dron | **Aprobada** (Brahian) |
| D4 | Dejar correr la V14 y arrancar la V15 desde su último checkpoint | **Aprobada** (ya corre) |
| D5 | 360° de entrada bajo (2.5 m, −3°, una vuelta, con guarda) y 360° de búsqueda alto (≥ 3.0 m, −8°) | **Aprobada** (idea de Brahian; cierra D-027) |
| D6 | Ladrón: en los niveles 0-1 solo se esconde; ataca desde el nivel 2 | **Aprobada** (Brahian) |
| D7 | Cuerpo de las personas con estadística colombiana; la altura segura del dron sale del alcance saltando | **Aprobada** (Brahian) |
