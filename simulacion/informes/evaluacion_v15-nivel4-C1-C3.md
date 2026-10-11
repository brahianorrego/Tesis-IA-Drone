# V15 · Ajustes del nivel 4 (C1-C3 del diagnóstico del supervisor)

Fecha: 2026-10-10. Encargo del arquitecto, aprobado por Brahian. Diagnóstico: `diagnostico_v15_nivel4.md`.
Medido con el modelo actual del entrenamiento (`modelos_v15/ultimo.zip`, 35.4 M pasos, copia de solo lectura) y su ladrón
congelado, sin reentrenar. Cada medición: 160 partidas en paralelo × 320 s, política estocástica (como al entrenar).
±2σ = 2·√(p(1−p)/n). Copias previas: `entorno_v15.py`, `entrenar_master_v15.py`, `index_v19.html`.

## Qué se cambió

**C1 · Pausa del contador (`entorno.py`, método nuevo `_contador`).**
- Si el dron re-adquiere al ladrón a lo sumo **4 s** (`T_PAUSA_REID`) después de perderlo, el contador continuo se
  **pausa**, aunque el dron haya pasado a un estado de búsqueda.
- Pasados los 4 s, la búsqueda lo reinicia como antes.
- Brahian eligió 4 s y no los 8 s del diagnóstico: más tiempo premiaría que el ladrón se muestre por error.

**C2 · Recompensa coherente (`entorno.py` y `entrenar_master.py`).**
- El tope de 5 min sin rendición es **terminal**, ya no `TimeLimit.truncated`, y cobra `R_TOPE = −5`.
- El éxito vale `R_EXITO = 5 + 0.25 × segundos restantes`: rendirlo antes nunca vale menos que seguir mirando.
- Solo actúa al entrenar; sin reentrenar no cambia ninguna medida de abajo.

**C3 · Métricas (`entorno.py` → `info`; `entrenar_master.py`).** Por partida se registran:
- vista acumulada;
- mejor racha del contador;
- T_rinde final;
- tiempo medio hasta re-adquirir (pérdidas de más de 1 s);
- tiempo en cada estado de búsqueda;
- desde qué estado se re-adquirió.

Dónde se publican:
- `salida/estado.json` → `curriculo.por_nivel`: el resumen de las últimas 1000 partidas de cada nivel.
- El log: una línea por nivel. En el nivel 4 va primero la **CUSTODIA**.
- El visor muestra la custodia del nivel 4 en el pie de "Dominio táctico".

**Definición de custodia.** Hay custodia si la vista acumulada en la partida llega a 60 s (o a 90 s), **o** si el ladrón se
rindió. La rendición termina la partida antes; si solo contara la vista acumulada, una rendición temprana parecería
"menos custodia". La primera medición, sin la rendición, daba ese efecto engañoso.

## Resultados (antes = código de la V15 sin C1-C3; después = con C1-C3)

### Nivel 4 · Misión completa (3 semillas por versión)

| Versión | Partidas | Rendición | Custodia ≥ 60 s | Custodia ≥ 90 s | Tope de 5 min | Racha mediana | Re-adquiere en |
|---|---:|---:|---:|---:|---:|---:|---:|
| Antes | 549 | 35.5 % ± 4.1 | 89.6 % | 82.9 % | 55.2 % | 33-40 s | 9.0 s |
| **Después (C1 con 4 s)** | 558 | **39.1 % ± 4.1** | **89.2 %** | **83.2 %** | 50.5 % | 37-38 s | 8.7 s |
| Referencia, sin aplicar: pausa de 8 s | 623 | 56.5 % ± 4.0 | 89.2 % | 83.0 % | 32.7 % | 44-45 s | 8.8 s |

T_rinde mediano: 44 s en las tres versiones.

### Niveles 0-3 (1 semilla por versión; ±2σ de 2-5 puntos)

| Nivel | Rendición antes | Rendición después | Custodia ≥ 60 s antes → después |
|---|---:|---:|---:|
| 0 Duelo abierto | 92.8 % (404) | 94.6 % (406) | 93.1 → 94.8 % |
| 1 Duelo con civil | 83.2 % (322) | 82.9 % (315) | 86.3 → 85.4 % |
| 2 Muro | 93.7 % (268) | 95.0 % (258) | 98.1 → 98.8 % |
| 3 Muro y civil | 82.9 % (205) | 81.5 % (205) | 97.1 → 98.5 % |

## Lectura

- **C1 con 4 s casi no mueve la rendición del nivel 4:** +3.6 puntos, con un margen de la diferencia de ±5.8, así que no
  es significativo. La razón está en las mismas métricas de C3: la re-adquisición media en el nivel 4 tarda ~9 s, y la
  mayoría de las pérdidas duran más de 4 s.
  - Con 8 s (solo como referencia) la rendición sube a 56.5 %, igual que el contrafactual del supervisor (47 %, con otra
    muestra).
  - La decisión de 4 s es de Brahian y se respeta. El dato queda para cuando se discuta.
- **Los niveles 0-3 no cambian** fuera del ruido. No hay más fallas: perdido, alcanzado y choques quedan igual.
- **La custodia del nivel 4 es alta y estable: ~89 % a 60 s y ~83 % a 90 s.** Es el número operativo para el caso policial,
  y el que se reporta como principal para el nivel 4.
- **C2 no se puede medir sin reentrenar.** Corrige la incoherencia de que perder por tiempo no costara nada. Su efecto
  esperado (diagnóstico: +5 puntos y menos entropía) se verá en el entrenamiento retomado.
- **C3 ya deja ver dónde se va el tiempo.** El tiempo por estado de búsqueda y el estado de re-adquisición quedan en
  `estado.json` para el próximo ciclo; la meta del supervisor es re-adquirir en ≤ 8 s.

## Pruebas

- `tests/test_nivel4.py` (7 pruebas):
  - la pausa con re-adquisición antes de 4 s;
  - el reinicio pasados 4 s;
  - el valor de 4 s;
  - R_EXITO y R_TOPE;
  - el tope terminal y su cobro;
  - que el master no trunque;
  - las métricas y el resumen con la custodia primero en el nivel 4.
- Batería completa: 82 pruebas pasan.
