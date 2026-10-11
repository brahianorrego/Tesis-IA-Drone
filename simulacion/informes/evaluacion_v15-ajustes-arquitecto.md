# V15 · Ajustes pedidos por el arquitecto tras la fase E

Fecha: 2026-10-10. Mismo modelo de la V14 (`dron_master_6999552_steps.zip`) y mismo ladrón congelado, **sin reentrenar**.
Copias previas: `entorno.py` y `mision.py` antes de estos ajustes quedaron en la carpeta temporal de la sesión (las copias
`*_v14.py` del repositorio siguen siendo las de antes de la V15).

## 1. Altura nominal = altura segura (3.30 m)

- `Z_NOMINAL = Z_SEGURA` (3.30 m): seguir, verificar y el 360° de búsqueda se vuelan fuera del alcance del ladrón y por
  encima de la burbuja de 2.6 m de los peatones. **Excepción:** el 360° de entrada (2.5 m, −3°) con su guarda de 6 m.
- Las observaciones de las redes siguen usando 2.3 m como referencia (`Z_REF_OBS`): el dron y el ladrón congelados ven
  la altura codificada igual que en la V14.
- El piloto de la fase 1 de `mision.py` sigue a 2.3 m (`Z_PILOTO`), como en el dron real antes de fijar.
- En los niveles 0 y 1 (que empiezan con el objetivo ya fijado) el dron nace a 3.30 m.
- Prueba `test_episodio_corto`: pedía que terminara alguna partida en 70 s con acciones al azar. Antes terminaban porque
  el ladrón alcanzaba al dron a 2.3 m; a 3.30 m la primera termina hacia los 134 s. Se amplió a 150 s (no es una regla
  dura). **62 pruebas pasan.**

### Rendición por nivel (éxito nuevo)

Dos corridas de 160 partidas en paralelo × 320 s por nivel (misma semilla del mundo y muestreo distinto de la política),
juntadas. ±2σ = 2·√(p(1−p)/n).

| Nivel | Antes (2.3 m, fase E) | Ahora (3.30 m) | n | ±2σ | Lo que más cambió |
|---|---:|---:|---:|---:|---|
| 0 Duelo abierto | 92 % | 89 % | 528 | ±2.7 | dentro del ruido; perdido 6-10 % |
| 1 Duelo con civil | 45 % | 51 % | 387 | ±5.1 | dentro del ruido |
| 2 Muro | 59 % | 66 % | 349 | ±5.1 | panel 14 % → 0 % |
| 3 Muro y civil | 5 % | 9 % | 322 | ±3.1 | peatón 5 % → 0 % |
| 4 Misión completa | 8 % | 12 % | 342 | ±3.5 | **alcanzado 23 % → 5 %**, peatón 1 % |

Lo que no es rendición en los niveles 2-4 es casi todo **"sin rendición en 5 min"** (tiempo 30-91 %), no fallas: es la
decisión abierta D-041 (el ladrón casi no se cansa: reserva al final 0.96-0.97, así que el contador pide ~117 s seguidos).

## 2. Muro de canto con desplazamiento lateral

Diseño nuevo (reemplaza el barrido de guiñada a 8 m de D-039):

1. Punto de canto a **6 m** de la punta cercana, en la prolongación del muro, con la nariz a lo largo del muro (1.5 s).
2. **1.0 m hacia el lado que dice la predicción** (media de la nube de partículas o, sin nube, la última posición), 2.5 s.
3. **1.0 m al otro lado** (cruza 2 m), 3.0 s. Una sola pasada, 7.0 s en total; la nariz no se mueve (error < 5°).
   Velocidad lateral con tope de 1 m/s; las guardas (LiDAR, geocerca, personas) siguen mandando.

### Maniobra aislada: ladrón quieto justo detrás de la punta lejana

Ladrón centrado en la línea del muro (±5 cm) y 0.3-1.0 m más allá de la punta lejana. 400 casos por fila. "Asoma" es la
fracción del cuerpo que ve la cámara (alto × ancho, con perspectiva y muro de 0.2 m).

| Muro | Diseño | Asoma de canto | Asoma máx. en la maniobra | Re-fijado (pred. acierta / falla) | Tiempo al re-fijado |
|---|---|---:|---:|---:|---:|
| 4 m | **nuevo, 6 m + lateral** | 15 % | **39 %** | 100 % / 99.5 % | 0.3 s |
| 4 m | anterior, 8 m + guiñada | 22 % | 30 % | 100 % / 100 % | 0.2 s |
| 6 m | **nuevo** | 10 % | **43 % / 40 %** | 99.8 % / 99.0 % | 1.0 s |
| 6 m | anterior | 14 % | 23 % | 99.8 % / 99.8 % | 0.4 s |
| 6.5 m | **nuevo** | 8 % | **41 % / 37 %** | 99.8 % / 99.2 % | 1.1-1.2 s |
| 6.5 m | anterior | 13 % | 23 % | 99.2 % / 98.8 % | 0.5 s |

- El cálculo 2D del arquitecto se confirma: de canto puro a 6 m asoma poco (24 % / 7 % en 2D; aquí 15 % / 8 % con el cuerpo
  en 3D), y con 1 m de lado asoma alrededor de un tercio (34 % / 33 % en 2D; aquí ~40 %).
- **En la simulación los dos diseños lo encuentran casi siempre**, porque el detector simulado ya dispara desde el 5 %
  visible (rampa hasta el 35 %). La ganancia del diseño nuevo es de **margen para el YOLO real**: casi el doble de cuerpo
  visible (~40 % frente a ~23 % con muros de 6-6.5 m). Cuesta 2.8 s más de maniobra.
- Cuando la predicción se equivoca de lado la diferencia es mínima (0-1 punto), porque la pasada cubre los dos lados.

### Escenarios fijos completos (política determinista, 100 partidas, éxito táctico de 30 s)

| Escenario | Cumplida | Re-adquiere en (s) | Notas |
|---|---:|---:|---|
| abierto | 100 % | 0.2 | |
| cambio brusco | 100 % | 1.1 | |
| tras muro | 100 % | 10.0 | |
| detrás de la punta (6 m) | 100 % | 9.7 | |
| detrás de la punta, muro de 4 m (nuevo) | 100 % | 5.9 | |
| detrás de la punta, muro de 6.5 m (nuevo) | 100 % | 8.3 | |
| cambia de lado | 100 % | 7.8 | |
| debajo | 84 % | 0.9 | perdido 16 %, **geocerca 0 %** |

Informe completo de la herramienta: `evaluacion_v15-z330-canto.md`.

## 3. Geocerca en cenit y en "debajo"

- "Debajo": geocerca **8 % → 0 %** (100 partidas).
- Nivel 0 (incluye las partidas de cenit): geocerca **0 %** en 528 partidas (antes 16 % en cenit). Lo arregló la guarda de
  geocerca de la fase E (frena con la distancia de frenado medida: 1.5 m/s², 0.5 s de retraso). No hizo falta tocar más.

## 4. Choques con peatones en el nivel 3

Origen: la burbuja de seguridad de los peatones es 1 m en horizontal **por debajo de 2.6 m**. Con la altura nominal de
2.3 m el dron estaba dentro de esa burbuja todo el tiempo que seguía al ladrón; por eso aparecían en el nivel 3 (5 %, 11 %
con −15°). **No venían de la guarda del 360° de entrada.**

Con 3.30 m (3 corridas de N3 y 4 de N4, 161 y 685 partidas):

| Nivel | Choques con peatón | Dónde |
|---|---:|---|
| 3 | 0 de 161 (0 %) | — |
| 4 | 4 de 685 (0.6 %) | **todos en el 360° de entrada bajo (2.5 m)**, a los 6-8 s de empezar |

Los 4 que quedan son el costo del 360° de entrada bajo aprobado: un civil se cruza a menos de 1 m antes de que la guarda
(6 m, solo con personas que la cámara ve) haga subir al dron. Propuesta, sin aplicar: que la guarda de entrada use también
las personas recordadas (como la guarda de personas de la fase E), o que el civil nazca a más de 6 m del dron.
