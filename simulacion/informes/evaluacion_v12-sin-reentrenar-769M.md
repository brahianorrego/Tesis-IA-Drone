# Evaluación en escenarios fijos · v12-sin-reentrenar-769M

Modelo: `modelos_master\checkpoints\dron_master_769612800_steps.zip`

Política determinista · 50 partidas por escenario · semillas 0.. · nivel de currículo 0.10 · máx. 120 s · 2026-10-10 10:16

## Resultados por escenario

| Escenario | Cumplida | Perdido | Alcanzado | Panel | Geocerca | Tiempo agotado | Duración (s) | A la vista | Pérdidas | Re-adquiere | t re-adq. (s) | Dist. mín. (m) | Altura máx. (m) | Gimbal mín/máx (°) | Recompensa | de ella, control | Jitter cabeceo (°/paso) | Jitter yaw (°/s/paso) | Jitter gimbal (°/s/paso) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| abierto | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 30.0 | 0.97 | 0.04 | 0.04 | 0.6 | 4.4 | 3.5 | -45 / 5 | 13.1 | -0.5 | 3.12 | 0.82 | 4.50 |
| cambio_brusco | 0.56 | 0.44 | 0.00 | 0.00 | 0.00 | 0.00 | 65.6 | 0.42 | 1.18 | 0.74 | 10.3 | 1.1 | 4.4 | -45 / 5 | 4.9 | -0.2 | 1.32 | 0.50 | 2.96 |
| tras_muro | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 42.6 | 0.69 | 1.08 | 1.08 | 12.3 | 3.1 | 5.0 | -45 / 2 | 14.5 | -0.1 | 0.79 | 0.34 | 1.99 |
| debajo | 0.00 | 0.98 | 0.00 | 0.00 | 0.02 | 0.00 | 91.7 | 0.04 | 1.12 | 0.14 | 1.1 | 0.0 | 5.5 | -45 / -9 | -10.9 | 0.0 | 1.29 | 1.05 | 1.33 |

Acciones elegidas con la IA al mando (fracción):

| Escenario | MANTENER | EVADIR_IZQ | EVADIR_DER | DETENER_ASCENDER | GIRAR_IZQ | GIRAR_DER | AVANZAR | DESCENDER | GIMBAL_ARRIBA | GIMBAL_ABAJO |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| abierto | 0.05 | 0.00 | 0.14 | 0.27 | 0.06 | 0.45 | 0.01 | 0.00 | 0.00 | 0.00 |
| cambio_brusco | 0.59 | 0.00 | 0.10 | 0.10 | 0.03 | 0.16 | 0.00 | 0.01 | 0.00 | 0.00 |
| tras_muro | 0.79 | 0.02 | 0.04 | 0.03 | 0.01 | 0.08 | 0.00 | 0.02 | 0.00 | 0.00 |
| debajo | 0.38 | 0.00 | 0.04 | 0.10 | 0.22 | 0.15 | 0.00 | 0.08 | 0.02 | 0.01 |
