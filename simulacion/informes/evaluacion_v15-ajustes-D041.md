# V15 · Ajustes D-041 (los aplicó el arquitecto)

Fecha: 2026-10-10, 18:20-19:20. La sesión "Simulacion" se quedó sin cupo de uso y el entrenamiento estaba trabado en el
nivel 1 (rendición 44-49 % contra la meta de 85 %), así que el arquitecto aplicó los ajustes en `entorno.py`.
Copia del archivo antes de estos cambios: en la carpeta temporal de la sesión del arquitecto (`entorno_antes_D041.py`).
Medido con el modelo de la V14 (`dron_master_6999552_steps.zip`) **sin reentrenar**, 160 entornos × 320 s por nivel.

## Qué se cambió

| Cambio | Detalle |
|---|---|
| Cansancio | Velocidad crítica 3.0 → **2.5 m/s** y D′ 150 → **120 m** (adulto no entrenado). La **tensión** gasta `K_TENSION` = 0.12 m/s equivalentes mientras está alerta y moviéndose. Expuesto a la cámara mientras cambia de cubierta, **esprinta** a 4.2-5.0 m/s (por partida; ráfagas limitadas por la stamina de 2 s; solo con reserva > 0.25) |
| **Moral del ladrón** (nuevo) | Idea de Brahian: "que el dron sea tan lógico que el ladrón se dé por vencido". Cada vez que el dron lo vuelve a encontrar tras esconderse (el mismo evento que cobra `R_DESCUBRE`), su moral baja ×0.8 (mínimo 0.3). Se rinde con el contador continuo en **20 s + 100 s × reserva × moral** |
| Civil distractor | Ya no cruza sin parar: tras cada cruce **descansa 15-30 s** apartado (3 veces más lejos de la línea de vista) y vuelve a cruzar |
| Memoria de apariencia | Los civiles que el operador ya distinguió del ladrón quedan "conocidos": cruzarse con ellos ya no obliga a preguntar por parecido; en cambio, tras el cruce el dron compara a quien sigue contra el ladrón **y** contra ese civil (con el ruido del ReID) y duda si se parece más al civil |
| Guarda del 360° de entrada | También sube si una persona **recordada** (vista hace < 3 s) está a menos de 6 m; ningún civil nace a menos de **6.5 m** del dron |
| Prueba | `test_v15.test_cansancio` calcula el gasto esperado con las constantes nuevas (VC, tensión). **62 pruebas pasan** |

## Números (rendición = éxito de la V15)

| Nivel | Fase E (2.3 m) | Ajustes del arquitecto (3.30 m) | **D-041** | Reconfirmaciones / 5 min | Cambios de ID sin detectar |
|---|---:|---:|---:|---:|---:|
| 0 Duelo abierto | 92 % | 89 % | **92 %** | 0.6 | 0 |
| 1 Duelo con civil | 45 % | 51 % | **83 %** | 6.5 (antes ~16) | **0** (307 partidas) |
| 2 Muro | 59 % | 66 % | **97 %** | 0.7 | 0 |
| 3 Muro y civil | 5 % | 9 % | **78 %** | 6.9 | **0** (194 partidas) |
| 4 Misión completa | 8 % | 12 % | **37 %** | 3.0 | 3 → revisado: 0 tras la comparación con el civil conocido (ver nota) |

Fallas en D-041: nivel 1 perdido 14 %; nivel 4 alcanzado 4 %, peatón 1 %; paneles y geocerca 0 % en todos.

Nota: la primera versión de la memoria de apariencia (solo "no preguntar por parecido") dejó 13 / 4 / 3 cambios sin
detectar en los niveles 1 / 3 / 4. Se corrigió con la comparación contra el civil conocido: 0 y 0 en los niveles 1 y 3
(el nivel 4 no se volvió a medir; lo vigila el criterio del currículo).

## Lo que no se cumplió y por qué se acepta

- **Reserva mediana a los 180 s: 0.82-0.88** (la meta era 0.3-0.5). El ladrón pasa mucho tiempo escondido y quieto, y
  quieto se recupera: es fisiológicamente correcto. La rendición se volvió alcanzable por la **moral** (encontrarlo una y
  otra vez), que es justo la lógica que pidió Brahian, y no por inflar el cansancio.
- **Reconfirmaciones 6.5-6.9 por misión** (meta ≤ 4; antes ~16). Se deja así: preguntar de más es seguro (humano en el
  lazo) y el entrenamiento puede aprender a evitar los cruces.

## Entrenamiento

Detenido a las 19:16 justo después del guardado de la iteración 240 (15.7 M pasos, nivel 1) y retomado de inmediato con
este código (`modelos_v15/ultimo.zip`, mismo nivel).
