# Evaluación en escenarios fijos · v12-referencia-modelo-v12 (entorno V12, mismo modelo que la evaluación V13)

Modelo: `..\..\..\..\AppData\Local\Temp\claude\C--Users-Brahi-Desktop-Claude\acb305c0-ec86-4acf-8f4d-4a0cb137aa56\scratchpad\v12_ultimo.zip`

Política determinista · 50 partidas por escenario · semillas 0.. · nivel de currículo 0.10 · máx. 120 s · 2026-10-10 11:50

## Resultados por escenario

| Escenario | Cumplida | Perdido | Alcanzado | Panel | Geocerca | Tiempo agotado | Duración (s) | A la vista | Pérdidas | Re-adquiere | t re-adq. (s) | Dist. mín. (m) | Altura máx. (m) | Gimbal mín/máx (°) | Recompensa | de ella, control | Jitter cabeceo (°/paso) | Jitter yaw (°/s/paso) | Jitter gimbal (°/s/paso) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| abierto | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 30.0 | 0.97 | 0.04 | 0.04 | 0.7 | 4.4 | 3.5 | -45 / 5 | 13.1 | -0.5 | 3.09 | 0.81 | 4.49 |
| cambio_brusco | 0.58 | 0.42 | 0.00 | 0.00 | 0.00 | 0.00 | 64.4 | 0.44 | 1.16 | 0.74 | 10.3 | 1.1 | 4.4 | -45 / 5 | 5.4 | -0.2 | 1.32 | 0.49 | 2.95 |
| tras_muro | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 45.6 | 0.65 | 1.28 | 1.28 | 12.6 | 2.9 | 5.2 | -45 / 2 | 14.5 | -0.1 | 0.83 | 0.39 | 1.96 |
| debajo | 0.00 | 0.96 | 0.00 | 0.00 | 0.04 | 0.00 | 90.3 | 0.06 | 1.12 | 0.14 | 1.1 | 0.1 | 5.5 | -45 / -6 | -10.8 | 0.0 | 1.62 | 1.01 | 1.44 |

Acciones elegidas con la IA al mando (fracción):

| Escenario | MANTENER | EVADIR_IZQ | EVADIR_DER | DETENER_ASCENDER | GIRAR_IZQ | GIRAR_DER | AVANZAR | DESCENDER | GIMBAL_ARRIBA | GIMBAL_ABAJO |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| abierto | 0.02 | 0.00 | 0.20 | 0.20 | 0.55 | 0.01 | 0.01 | 0.00 | 0.00 | 0.00 |
| cambio_brusco | 0.34 | 0.00 | 0.12 | 0.09 | 0.45 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| tras_muro | 0.70 | 0.01 | 0.09 | 0.03 | 0.14 | 0.00 | 0.00 | 0.01 | 0.00 | 0.01 |
| debajo | 0.12 | 0.00 | 0.06 | 0.01 | 0.71 | 0.00 | 0.00 | 0.05 | 0.00 | 0.03 |
