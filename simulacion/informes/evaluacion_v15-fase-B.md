# V15 · Fase B · Predicción

Fecha: 2026-10-10. Plan: `docs/PLAN_V15_CURRICULO.md` (sección 4A y fase B de la sección 7). Medido con el último modelo
de la V14 (`dron_master_6999552_steps.zip`) **sin reentrenar**. Observación (192) y acciones (10) sin cambiar.

## Qué se hizo (`entorno.py`)

| Pieza | Detalle |
|---|---|
| **Kalman** | Aceleración constante por eje (posición, velocidad, aceleración), jerk `KF_Q` = 8. Reemplaza el EMA de `tvx/tvy`. **Compuerta**: una medición a más de 4σ (y > 1 m) se descarta; tres seguidas reinician el filtro. Sin medición, la aceleración se apaga (×0.7 por paso), la rapidez no pasa de 4 m/s y la posición queda en la arena |
| **Medición geométrica** | Con la persona a más de 12° bajo el horizonte, la distancia sale de la altura del dron y del ángulo (suelo plano), no del bbox (que llega cortado cuando está debajo). La Jetson real tiene esos datos |
| **Filtro de partículas** | 200 hipótesis por dron, nacen del Kalman al perderlo de vista. Movimiento humano (aceleración aleatoria 2 m/s², máx. 4 m/s), **no atraviesan muros**, quedan en la arena. **Información negativa**: las que la cámara ve (en cuadro, sin muro delante, < 30 m) sin que YOLO detecte a nadie conservan el 5 % del peso. Remuestreo sistemático; si la nube muere, se vuelve a esparcir |
| **Observación** | Las columnas "dónde estaría ahora" se llenan con la media de la nube (sin verlo) o el Kalman (a la vista); "velocidad/escape" con el Kalman |
| **Búsqueda guiada** | PÉRDIDA va hacia la media de la nube (sin acercarse a menos de 4 m, y sin avanzar si un muro del mapa queda en medio) y la nariz la sigue; el flanqueo elige el **muro con más masa detrás** (≥ 25 %) y la esquina por su centroide; SIGUIENTE_OBSTÁCULO prefiere muros con masa; el GIRO_360 empieza hacia la masa |
| **Anti-cenit predictivo** | Si el Kalman dice que entra a la zona ciega en menos de 1.2 s, la nariz gira ya hacia el **punto de salida** (120°/s). Durante el anti-cenit y el reflejo de punto ciego el dron **sube a la altura segura** (sin eso, "cambio brusco" bajaba a 76 %: al girar la nariz el árbitro no ve al ladrón, que lo alcanzaba con el brazo a 2.3 m) |
| **Distancia adaptativa** | Si se acerca a > 1 m/s: separación = zona ciega + v²/(2·2.5) + 0.5·v (hasta 7 m; ≈ 6 m a 3.4 m/s). Cerca del borde de la arena el retroceso se curva hacia la tangente que va al centro y frena con la distancia de frenado (sin eso, "debajo" fallaba por geocerca en el 52 %) |

Errores encontrados y corregidos en el camino: el Kalman divergía (medición por bbox con el ladrón debajo → 6 m/s al
revés → la predicción se iba a 47 m, fuera de la arena, y la nube nacía en el lado equivocado).

## Números

Escenarios fijos (50 partidas, política determinista):

| Escenario | Fase A | **Fase B** | Criterio |
|---|---|---|---|
| abierto | 100 % | **100 %** | — |
| cambio brusco | 98 % | **100 %** (a la vista 74 → 89 %) | se mantiene en 100 % ✔ |
| tras muro | 100 % | **100 %** | — |
| **debajo** | 4 % | **68 %** (a la vista 7 → 67 %; geocerca 8 %) | > 0 % ✔ (meta 70 %) |

Entorno de entrenamiento (192 entornos × 150 s, misma semilla, uno detrás del otro):

| Caso | Fase A | Fase B |
|---|---|---|
| Cenit puro (nivel 0, todas las partidas de cenit) | 0 % (perdido 66 %, alcanzado 33 %) | **50 %** (perdido 12 %, alcanzado 21 %, geocerca 16 %) |
| Nivel 0 (V14) | 70 % | **87 %** |
| Nivel 1 | 92 % | 89 % (panel 8 %) |
| Nivel 2 | 88 % | 87 % (panel 7 %) |
| Nivel 3 | 63 % | **69 %** (perdido 2 → 0 %, alcanzado 23 → 17 %) |

Velocidad: ~10 % menos que la fase A (las partículas solo corren en los drones que lo perdieron).

## Lo que queda abierto
- El cenit puro llega a 50 % sin reentrenar; lo que falla es que lo alcance (21 %) y la geocerca (16 %). El nivel 0 del
  currículo (fase E) exige cenit ≥ 70 %: es lo que el entrenamiento tiene que aprender.
- La búsqueda con partículas usa el generador aleatorio del simulador: sigue siendo determinista en el sentido de la
  regla 3 (no la decide la red), pero no es reproducible paso a paso sin la misma semilla.

## Pruebas
50 pasan. Nuevas (`tests/test_v15.py`, clase `TestFaseB`): el Kalman converge y rechaza mediciones imposibles; las
partículas no atraviesan muros; la información negativa vacía lo que la cámara ve y deja la masa detrás del muro; la
separación adaptativa sube por encima de la zona ciega con un ladrón que carga.

---

## Anexo · salida de herramientas/evaluar_politica.py (entorno V15-B)

### Evaluación en escenarios fijos · v15-fase-B

Modelo: `..\..\..\..\AppData\Local\Temp\claude\C--Users-Brahi-Desktop-Claude\acb305c0-ec86-4acf-8f4d-4a0cb137aa56\scratchpad\v14_ultimo.zip`

Política determinista · 50 partidas por escenario · semillas 0.. · nivel de currículo 0.10 · máx. 120 s · 2026-10-10 14:27

## Resultados por escenario

| Escenario | Cumplida | Perdido | Alcanzado | Panel | Geocerca | Tiempo agotado | Duración (s) | A la vista | Pérdidas | Re-adquiere | t re-adq. (s) | Dist. mín. (m) | Altura máx. (m) | Gimbal mín/máx (°) | Recompensa | de ella, control | Jitter cabeceo (°/paso) | Jitter yaw (°/s/paso) | Jitter gimbal (°/s/paso) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| abierto | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 30.0 | 0.97 | 0.02 | 0.02 | 0.1 | 4.7 | 3.1 | -45 / 7 | 13.5 | -0.8 | 2.99 | 1.03 | 4.53 |
| cambio_brusco | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 32.0 | 0.89 | 2.20 | 2.20 | 0.9 | 1.4 | 5.1 | -45 / 3 | 14.1 | -0.2 | 1.40 | 1.45 | 2.90 |
| tras_muro | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 43.1 | 0.67 | 1.28 | 1.28 | 10.9 | 3.2 | 4.5 | -45 / 2 | 15.7 | -0.2 | 0.64 | 0.57 | 1.62 |
| debajo | 0.68 | 0.24 | 0.00 | 0.00 | 0.08 | 0.00 | 45.6 | 0.67 | 2.34 | 2.10 | 1.0 | 1.6 | 5.3 | -45 / -2 | 7.2 | -0.1 | 2.26 | 5.66 | 3.83 |

Acciones elegidas con la IA al mando (fracción):

| Escenario | MANTENER | EVADIR_IZQ | EVADIR_DER | DETENER_ASCENDER | GIRAR_IZQ | GIRAR_DER | AVANZAR | DESCENDER | GIMBAL_ARRIBA | GIMBAL_ABAJO |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| abierto | 0.01 | 0.01 | 0.16 | 0.09 | 0.22 | 0.34 | 0.05 | 0.05 | 0.04 | 0.02 |
| cambio_brusco | 0.09 | 0.02 | 0.18 | 0.05 | 0.18 | 0.23 | 0.02 | 0.09 | 0.04 | 0.08 |
| tras_muro | 0.26 | 0.13 | 0.10 | 0.03 | 0.02 | 0.07 | 0.02 | 0.08 | 0.11 | 0.17 |
| debajo | 0.16 | 0.03 | 0.06 | 0.01 | 0.09 | 0.12 | 0.00 | 0.11 | 0.13 | 0.29 |
