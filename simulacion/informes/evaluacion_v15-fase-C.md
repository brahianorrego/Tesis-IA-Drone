# V15 · Fase C · Identidad

Fecha: 2026-10-10. Plan: `docs/PLAN_V15_CURRICULO.md` (sección 4E y fase C de la sección 7). Medido con el último
modelo de la V14 **sin reentrenar**.

## Qué se hizo (`entorno.py`)

| Pieza | Detalle |
|---|---|
| Apariencia | Cada persona tiene un vector de apariencia (8 números: ropa, contextura). Cada civil se parece al ladrón con coseno entre 0.2 y 0.97 (a veces visten casi igual) |
| **Cambio de ID** | Con el objetivo designado, si otra persona visible se superpone en la imagen con la persona seguida (bboxes que se tocan), el tracker salta a ella con probabilidad 0.3 · parecido² · (1 − diferencia de velocidad / 2 m/s, mínimo 0.15) por cuadro |
| Percepción del dron | La columna 0 de todo lo que mide el dron es **la persona que el tracker sigue**: con un cambio sin detectar, el dron persigue al otro (como pasaría de verdad). El ladrón, las recompensas, el tiempo de rastreo y las métricas usan la verdad (`visible_real`, `trk == 0`) |
| ReID | Parecido medido de la persona seguida con la que designó el operador (ruido 0.03 + 0.01·distancia), promediado (α 0.2) |
| **RECONFIRMAR** (estado 9) | Duda si: el ReID promediado baja de 0.85; o, en los 3 s tras un cruce, se cruzó con alguien parecido (> 0.8) o el Kalman rechazó mediciones; o quedó un cruce sin verificar (lo perdió de vista) y lo vuelve a fijar. Hover con el objetivo en cuadro (el árbitro sigue mandando si hay que esquivar) y alerta al operador; en 1-2 s hace clic sobre el ladrón si lo ve. Si no lo ve y el dron seguía a otro: "no es él" → PÉRDIDA desde donde estaba el cruce (Kalman y nube arrancan ahí). La red no decide en este estado |
| Métricas (`info`) | `id_ok` (tiempo con la persona correcta), `cambio` (el cruce terminó con el tracker en otra persona), `cambio_det`, `cambio_nodet` (persigue más de 1 s a la persona equivocada sin haber dudado), `reconf` |

## Números (192-256 entornos, misma semilla)

| Escenario | Partidas | ID correcto | Cambios | Detectados | **Sin detectar** | Reconfirmaciones |
|---|---|---|---|---|---|---|
| Duelo con civil que se cruza (nivel 1 del plan) | 1 556 | 96.3 % del tiempo | 891 | todos | **0** | 3 354 (2.2 por partida) |
| Nivel 2 de la V14 (muro + civil) | 284 | 96.8 % | 470 | todos | **0** | 1 863 |

Duelo con civil: cumplida 74 %, alcanzado 13 %, choque con peatón 3 %. Escenarios fijos sin cambios (abierto 100 %,
cambio brusco 98 %, tras muro 100 %, debajo 66 %).

Iteraciones que hicieron falta para llegar a 0 (para documentar):
1. La primera métrica contaba como error los saltos de ida y vuelta mientras las dos personas siguen superpuestas
   (el tracker reasociando): 463 "sin detectar". Se cuenta cuando el cruce terminó.
2. Quedaban cruces sin verificar porque el dron perdió de vista a todos justo después: se agregó la **duda pendiente**.
3. Las dudas esperaban a que terminara una evasión: ahora se pregunta al operador mientras el árbitro esquiva.

## Criterio de aceptación de la fase C
- 0 cambios sin detectar en 1000 partidas del nivel 1: **sí** (0 en 1 556).
- Para el currículo (fase E), el nivel 1 pide además ID correcto ≥ 98 % del tiempo: hoy 96.3 % sin entrenar.

## Pruebas
53 pasan. Nuevas en `tests/test_v15.py` (`TestFaseC`): con alguien casi igual el tracker se confunde, el dron duda
y el operador lo devuelve al ladrón sin ningún cambio sin detectar; con alguien muy distinto casi no se confunde; la
red no decide en RECONFIRMAR.

**Prueba de reglas duras modificada (para que Brahian lo revise):** `test_reglas_duras.py` agrega el estado
RECONFIRMAR a las transiciones permitidas (PERSECUCIÓN → RECONFIRMAR → PERSECUCIÓN/PÉRDIDA) y **endurece** la regla del
humano en el lazo: de RECONFIRMAR solo se vuelve a PERSECUCIÓN después del tiempo de respuesta del operador y siempre
con la persona correcta.

---

## Anexo · salida de herramientas/evaluar_politica.py (entorno V15-C)

### Evaluación en escenarios fijos · v15-fase-C

Modelo: `..\..\..\..\AppData\Local\Temp\claude\C--Users-Brahi-Desktop-Claude\acb305c0-ec86-4acf-8f4d-4a0cb137aa56\scratchpad\v14_ultimo.zip`

Política determinista · 50 partidas por escenario · semillas 0.. · nivel de currículo 0.10 · máx. 120 s · 2026-10-10 15:13

## Resultados por escenario

| Escenario | Cumplida | Perdido | Alcanzado | Panel | Geocerca | Tiempo agotado | Duración (s) | A la vista | Pérdidas | Re-adquiere | t re-adq. (s) | Dist. mín. (m) | Altura máx. (m) | Gimbal mín/máx (°) | Recompensa | de ella, control | Jitter cabeceo (°/paso) | Jitter yaw (°/s/paso) | Jitter gimbal (°/s/paso) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| abierto | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 30.3 | 0.97 | 0.00 | 0.00 | -- | 4.8 | 2.8 | -45 / 8 | 13.7 | -0.7 | 2.83 | 0.96 | 4.50 |
| cambio_brusco | 0.98 | 0.00 | 0.02 | 0.00 | 0.00 | 0.00 | 31.5 | 0.89 | 2.08 | 2.06 | 0.8 | 1.4 | 5.1 | -45 / 5 | 13.7 | -0.2 | 1.42 | 1.60 | 2.97 |
| tras_muro | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 44.8 | 0.65 | 1.52 | 1.52 | 11.3 | 3.2 | 4.6 | -45 / 3 | 15.6 | -0.2 | 0.71 | 0.64 | 1.74 |
| debajo | 0.66 | 0.32 | 0.00 | 0.00 | 0.02 | 0.00 | 52.0 | 0.61 | 2.62 | 2.30 | 1.1 | 1.7 | 5.4 | -45 / -1 | 6.3 | -0.1 | 2.45 | 6.13 | 3.48 |

Acciones elegidas con la IA al mando (fracción):

| Escenario | MANTENER | EVADIR_IZQ | EVADIR_DER | DETENER_ASCENDER | GIRAR_IZQ | GIRAR_DER | AVANZAR | DESCENDER | GIMBAL_ARRIBA | GIMBAL_ABAJO |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| abierto | 0.01 | 0.01 | 0.16 | 0.10 | 0.22 | 0.33 | 0.05 | 0.06 | 0.04 | 0.03 |
| cambio_brusco | 0.10 | 0.03 | 0.17 | 0.04 | 0.16 | 0.25 | 0.02 | 0.08 | 0.05 | 0.09 |
| tras_muro | 0.21 | 0.15 | 0.14 | 0.03 | 0.02 | 0.07 | 0.02 | 0.12 | 0.12 | 0.13 |
| debajo | 0.16 | 0.03 | 0.04 | 0.01 | 0.07 | 0.10 | 0.00 | 0.11 | 0.14 | 0.33 |
