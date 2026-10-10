# Evaluación en escenarios fijos · v10-763M-con-reglas-v11

Modelo: `modelos_master\checkpoints\dron_master_762613248_steps.zip`

Política determinista · 50 partidas por escenario · semillas 0.. · nivel de currículo 0.10 · máx. 120 s · 2026-10-10 09:22

## Resultados por escenario

| Escenario | Cumplida | Perdido | Alcanzado | Panel | Geocerca | Tiempo agotado | Duración (s) | A la vista | Pérdidas | Re-adquiere | t re-adq. (s) | Dist. mín. (m) | Altura máx. (m) | Gimbal mín/máx (°) | Recompensa | de ella, control | Jitter cabeceo (°/paso) | Jitter yaw (°/s/paso) | Jitter gimbal (°/s/paso) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| abierto | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 30.0 | 0.97 | 0.00 | 0.00 | -- | 4.4 | 3.5 | -45 / 5 | -5.3 | -18.9 | 3.14 | 0.82 | 4.49 |
| cambio_brusco | 0.60 | 0.40 | 0.00 | 0.00 | 0.00 | 0.00 | 35.9 | 0.52 | 1.12 | 0.72 | 9.9 | 1.3 | 4.3 | -45 / 5 | -2.1 | -6.5 | 1.31 | 0.51 | 2.92 |
| tras_muro | 0.94 | 0.06 | 0.00 | 0.00 | 0.00 | 0.00 | 41.4 | 0.66 | 1.02 | 0.96 | 11.7 | 3.2 | 4.9 | -45 / 2 | 8.1 | -4.0 | 0.69 | 0.51 | 1.44 |
| debajo | 0.00 | 0.94 | 0.06 | 0.00 | 0.00 | 0.00 | 22.4 | 0.11 | 1.04 | 0.10 | 2.1 | 0.0 | 5.3 | -45 / -11 | -7.8 | -0.1 | 0.09 | 1.14 | 0.92 |

Acciones elegidas con la IA al mando (fracción):

| Escenario | MANTENER | EVADIR_IZQ | EVADIR_DER | DETENER_ASCENDER | GIRAR_IZQ | GIRAR_DER | AVANZAR | DESCENDER | GIMBAL_ARRIBA | GIMBAL_ABAJO |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| abierto | 0.06 | 0.04 | 0.18 | 0.36 | 0.01 | 0.19 | 0.01 | 0.01 | 0.00 | 0.15 |
| cambio_brusco | 0.47 | 0.01 | 0.20 | 0.13 | 0.01 | 0.05 | 0.00 | 0.02 | 0.00 | 0.11 |
| tras_muro | 0.58 | 0.18 | 0.07 | 0.05 | 0.00 | 0.04 | 0.00 | 0.00 | 0.00 | 0.07 |
| debajo | 0.38 | 0.02 | 0.21 | 0.14 | 0.06 | 0.09 | 0.00 | 0.00 | 0.00 | 0.11 |
