# Evaluación en escenarios fijos · v10-master-350M

Modelo: `modelos_master\checkpoints\dron_master_350639616_steps.zip`

Política determinista · 50 partidas por escenario · semillas 0.. · nivel de currículo 0.10 · máx. 120 s · 2026-10-10 08:57

## Resultados por escenario

| Escenario | Cumplida | Perdido | Alcanzado | Panel | Geocerca | Tiempo agotado | Duración (s) | A la vista | Pérdidas | Re-adquiere | t re-adq. (s) | Dist. mín. (m) | Altura máx. (m) | Gimbal mín/máx (°) | Recompensa | de ella, control | Jitter cabeceo (°/paso) | Jitter yaw (°/s/paso) | Jitter gimbal (°/s/paso) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| abierto | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 30.0 | 0.97 | 0.00 | 0.00 | -- | 4.4 | 3.4 | -44 / 5 | -5.4 | -19.0 | 3.20 | 0.82 | 4.49 |
| cambio_brusco | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 67.4 | 0.09 | 1.00 | 0.00 | -- | 1.4 | 3.5 | -42 / 2 | -8.0 | -4.1 | 0.26 | 0.05 | 0.32 |
| tras_muro | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 65.7 | 0.07 | 1.00 | 0.00 | -- | 5.1 | 3.0 | -25 / 2 | -10.5 | -4.4 | 0.36 | 0.09 | 0.21 |
| debajo | 0.00 | 0.56 | 0.00 | 0.00 | 0.44 | 0.00 | 54.5 | 0.03 | 1.00 | 0.00 | -- | 0.0 | 4.2 | -39 / -11 | -7.7 | -1.0 | 0.11 | 0.02 | 0.03 |

Acciones elegidas con la IA al mando (fracción):

| Escenario | MANTENER | EVADIR_IZQ | EVADIR_DER | DETENER_ASCENDER | GIRAR_IZQ | GIRAR_DER | AVANZAR | DESCENDER | GIMBAL_ARRIBA | GIMBAL_ABAJO |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| abierto | 0.01 | 0.01 | 0.24 | 0.26 | 0.31 | 0.11 | 0.01 | 0.05 | 0.00 | 0.00 |
| cambio_brusco | 0.12 | 0.04 | 0.21 | 0.30 | 0.04 | 0.01 | 0.00 | 0.29 | 0.00 | 0.00 |
| tras_muro | 0.08 | 0.12 | 0.21 | 0.28 | 0.03 | 0.01 | 0.00 | 0.28 | 0.00 | 0.00 |
| debajo | 0.00 | 0.07 | 0.10 | 0.40 | 0.02 | 0.00 | 0.00 | 0.41 | 0.00 | 0.00 |
