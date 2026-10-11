# Evaluación en escenarios fijos · v15-ref-entorno-v14

Modelo: `v14_ultimo.zip`

Política determinista · 50 partidas por escenario · semillas 0.. · nivel de currículo 0.10 · máx. 120 s · 2026-10-10 14:16

## Resultados por escenario

| Escenario | Cumplida | Perdido | Alcanzado | Panel | Geocerca | Tiempo agotado | Duración (s) | A la vista | Pérdidas | Re-adquiere | t re-adq. (s) | Dist. mín. (m) | Altura máx. (m) | Gimbal mín/máx (°) | Recompensa | de ella, control | Jitter cabeceo (°/paso) | Jitter yaw (°/s/paso) | Jitter gimbal (°/s/paso) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| abierto | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 30.0 | 0.97 | 0.00 | 0.00 | -- | 4.7 | 2.8 | -45 / 6 | 13.7 | -0.6 | 2.92 | 0.86 | 4.41 |
| cambio_brusco | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 38.5 | 0.75 | 1.22 | 1.22 | 8.0 | 1.0 | 4.2 | -45 / 4 | 14.6 | -0.3 | 0.86 | 0.52 | 2.36 |
| tras_muro | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 40.4 | 0.71 | 1.04 | 1.04 | 10.2 | 3.5 | 4.1 | -45 / 3 | 15.5 | -0.1 | 0.57 | 0.48 | 1.31 |
| debajo | 0.02 | 0.96 | 0.02 | 0.00 | 0.00 | 0.00 | 90.7 | 0.04 | 1.20 | 0.22 | 2.5 | 0.0 | 5.5 | -45 / -8 | -10.6 | -0.0 | 1.43 | 1.04 | 1.71 |

Acciones elegidas con la IA al mando (fracción):

| Escenario | MANTENER | EVADIR_IZQ | EVADIR_DER | DETENER_ASCENDER | GIRAR_IZQ | GIRAR_DER | AVANZAR | DESCENDER | GIMBAL_ARRIBA | GIMBAL_ABAJO |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| abierto | 0.01 | 0.01 | 0.17 | 0.14 | 0.21 | 0.33 | 0.03 | 0.02 | 0.03 | 0.04 |
| cambio_brusco | 0.15 | 0.01 | 0.12 | 0.06 | 0.42 | 0.20 | 0.01 | 0.00 | 0.03 | 0.01 |
| tras_muro | 0.13 | 0.16 | 0.06 | 0.02 | 0.01 | 0.08 | 0.00 | 0.04 | 0.40 | 0.10 |
| debajo | 0.14 | 0.00 | 0.03 | 0.01 | 0.44 | 0.14 | 0.00 | 0.03 | 0.09 | 0.12 |
