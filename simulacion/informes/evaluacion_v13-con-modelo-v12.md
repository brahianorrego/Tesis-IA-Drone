# Evaluación en escenarios fijos · v13-con-modelo-v12

Modelo: `..\..\..\..\AppData\Local\Temp\claude\C--Users-Brahi-Desktop-Claude\acb305c0-ec86-4acf-8f4d-4a0cb137aa56\scratchpad\v12_ultimo.zip`

Política determinista · 50 partidas por escenario · semillas 0.. · nivel de currículo 0.10 · máx. 120 s · 2026-10-10 11:48

## Resultados por escenario

| Escenario | Cumplida | Perdido | Alcanzado | Panel | Geocerca | Tiempo agotado | Duración (s) | A la vista | Pérdidas | Re-adquiere | t re-adq. (s) | Dist. mín. (m) | Altura máx. (m) | Gimbal mín/máx (°) | Recompensa | de ella, control | Jitter cabeceo (°/paso) | Jitter yaw (°/s/paso) | Jitter gimbal (°/s/paso) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| abierto | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 30.0 | 0.97 | 0.00 | 0.00 | -- | 4.6 | 3.5 | -45 / 5 | 13.1 | -0.6 | 3.18 | 0.81 | 4.53 |
| cambio_brusco | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 38.7 | 0.74 | 1.18 | 1.18 | 8.2 | 1.0 | 3.6 | -45 / 6 | 13.9 | -0.2 | 0.84 | 0.56 | 2.26 |
| tras_muro | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 40.4 | 0.71 | 1.04 | 1.04 | 10.2 | 3.6 | 4.0 | -45 / 4 | 15.9 | -0.1 | 0.52 | 0.44 | 1.31 |
| debajo | 0.08 | 0.90 | 0.00 | 0.00 | 0.02 | 0.00 | 88.0 | 0.09 | 1.30 | 0.40 | 1.2 | 0.0 | 5.6 | -45 / -2 | -8.9 | 0.0 | 1.04 | 1.03 | 1.42 |

Acciones elegidas con la IA al mando (fracción):

| Escenario | MANTENER | EVADIR_IZQ | EVADIR_DER | DETENER_ASCENDER | GIRAR_IZQ | GIRAR_DER | AVANZAR | DESCENDER | GIMBAL_ARRIBA | GIMBAL_ABAJO |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| abierto | 0.02 | 0.00 | 0.20 | 0.21 | 0.55 | 0.01 | 0.01 | 0.00 | 0.00 | 0.00 |
| cambio_brusco | 0.21 | 0.00 | 0.11 | 0.08 | 0.59 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| tras_muro | 0.77 | 0.01 | 0.06 | 0.03 | 0.12 | 0.00 | 0.00 | 0.01 | 0.00 | 0.00 |
| debajo | 0.31 | 0.00 | 0.15 | 0.02 | 0.45 | 0.00 | 0.00 | 0.03 | 0.00 | 0.03 |
