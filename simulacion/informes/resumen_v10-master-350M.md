# Resumen de entrenamiento · v10-master-350M

Corrida: salida\metricas.json · 5350 iteraciones · 350.6 M pasos · motor Stable-Baselines3 PPO · nivel de currículo actual 0.04.
Ventana actual = últimas 50 iteraciones (3.3 M pasos, 4231 partidas de entrenamiento, política estocástica).

## Indicadores (ventana actual vs anterior)

| Indicador | Actual | Anterior | Inicio de la corrida | Cambio |
|---|---:|---:|---:|---|
| Misión cumplida (éxito) | 25 % | 25 % | 30 % | = |
| Perdido (búsqueda agotada) | 49 % | 50 % | 46 % | = |
| No encontrado | 1 % | 1 % | 1 % | = |
| Alcanzado por el ladrón | 13 % | 13 % | 14 % | = |
| Choque con peatón (partidas con peatones) | 9 % | 8 % | 8 % | = |
| Choque con panel | 2 % | 2 % | 2 % | = |
| Sale de la geocerca | 2 % | 1 % | 1 % | = |
| Tiempo con el objetivo a la vista | 17 % | 17 % | 17 % | = |
| Duración media de la partida (s, estimada) | 77.4 | 76.6 | 76.0 |  |
| Recompensa total por partida | -7.19 | -7.19 | -7.50 | = |
|   de ella, castigo de control (jitter + esfuerzo) | 6.94 | 6.95 | 7.90 | = |
| Pérdidas del objetivo por partida | 2.58 | 2.49 | 3.23 | = |
| Re-adquisiciones por partida | 2.18 | 2.08 | 2.81 | = |
| Jitter: Σ|Δu| por paso con la IA al mando (3 ejes) | 0.042 | 0.042 | 0.051 | = |
| Entropía de la política (máx. 2.30) | 1.62 | 1.61 | 1.41 |  |

Acciones (ventana actual, %): decide con el objetivo fijado / en la búsqueda tras perderlo.

| MANTENER | EVADIR_IZ | EVADIR_DE | DETENER_A | GIRAR_IZQ | GIRAR_DER | AVANZAR | DESCENDER | GIMBAL_AR | GIMBAL_AB |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 16 / 16 | 18 / 19 | 19 / 20 | 19 / 21 | 2 / 0 | 1 / 0 | 0 / 0 | 19 / 19 | 1 / 0 | 5 / 4 |
En la búsqueda casi nunca usa: GIRAR_IZQ, GIRAR_DER, AVANZAR.

## Tendencia por tramos de 50 M pasos

| M pasos | Cumplida | Perdido | Alcanzado | Panel | Geocerca | Dur. (s) | Recompensa | Σ|Δu|/paso | Entropía | Nivel |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0-50 | 32 % | 43 % | 15 % | 2 % | 1 % | 74 | -7.5 | 0.051 | 1.50 | 0.19 |
| 50-100 | 34 % | 41 % | 15 % | 2 % | 1 % | 74 | -7.4 | 0.053 | 1.58 | 0.27 |
| 100-150 | 33 % | 41 % | 14 % | 2 % | 2 % | 74 | -7.4 | 0.052 | 1.58 | 0.23 |
| 150-200 | 28 % | 46 % | 14 % | 2 % | 2 % | 77 | -7.5 | 0.047 | 1.60 | 0.11 |
| 200-250 | 25 % | 49 % | 13 % | 2 % | 2 % | 78 | -7.5 | 0.043 | 1.61 | 0.02 |
| 250-300 | 24 % | 49 % | 13 % | 2 % | 2 % | 78 | -7.4 | 0.042 | 1.61 | 0.01 |
| 300-350 | 25 % | 49 % | 13 % | 2 % | 1 % | 79 | -7.4 | 0.043 | 1.61 | 0.02 |
| 350-351 | 27 % | 45 % | 14 % | 2 % | 2 % | 76 | -7.1 | 0.043 | 1.61 | 0.01 |
Pendiente de la tasa de cumplidas en los últimos 100 M pasos: +2.4 puntos por cada 100 M (ruido por iteración ±5 puntos).

## Escenarios fijos (evaluar_politica.py)

Fuente: `barrido_v10-master.csv` (política determinista, mismas semillas).

| M pasos | cumplida abierto | cumplida cambio_brusco | cumplida tras_muro | cumplida debajo | alcanzado | jitter cab/yaw/gmb |
|---:|---:|---:|---:|---:|---:|---:|
| 250 | 100 % | 0 % | 0 % | 20 % | 0 % | 0.97 / 0.27 / 1.28 |
| 275 | 100 % | 0 % | 0 % | 0 % | 0 % | 0.98 / 0.25 / 1.26 |
| 300 | 100 % | 0 % | 0 % | 2 % | 0 % | 0.96 / 0.25 / 1.26 |
| 325 | 100 % | 0 % | 0 % | 0 % | 0 % | 0.99 / 0.25 / 1.26 |
| 350 | 100 % | 0 % | 0 % | 0 % | 0 % | 0.98 / 0.25 / 1.26 |

## Lo que no se registra (y cómo registrarlo en el próximo entrenamiento)

- No hay logs de TensorBoard (SB3 se lanzó sin `tensorboard_log`).
- Duración real de la partida: aquí se estima como pasos / partidas terminadas. Guardar `ep_len` en `VecDron.fin` (entrenar_master.py) y su media en `resumen()`.
- Recompensa por componente: solo se separa el castigo de control. Acumular cada término de `rew_d` (vista, rango, guía, descubre, pierde, maniobra, éxito, fallas, control) en `info["r_comp"]` dentro de `entorno.step` y promediarlo por partida en `VecDron`.
- Jitter por eje (cabeceo, yaw, gimbal): hoy se guarda la suma de los 3. Devolver `|u - u_prev|` por eje en `info` y guardar 3 promedios en `m["control"]`. Mientras tanto, el barrido de escenarios fijos sí lo mide.
- Gimbal mínimo alcanzado (regla dura -60°): guardar `min(cam_pitch)` por iteración.
