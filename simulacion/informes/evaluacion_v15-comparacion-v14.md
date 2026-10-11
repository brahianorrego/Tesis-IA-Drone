# V14 contra V15 por nivel: ¿la V15 es peor?

Fecha: 2026-10-10. Mismo modelo del dron (`dron_master_6999552_steps.zip`, V14, sin reentrenar) y mismo ladrón congelado.
160 partidas en paralelo × 320 s por nivel, política estocástica (como en el entrenamiento). La V15 medida es la versión
completa (fases A-E y los ajustes del arquitecto: altura nominal 3.30 m y canto lateral).
n = partidas terminadas; ±2σ = 2·√(p(1−p)/n), el margen de ruido de cada porcentaje.

## La pregunta

En la V15 el éxito por nivel se ve mucho más bajo que en la V14. Hay tres explicaciones posibles y se separan midiendo:

1. **Otro criterio de éxito.** V14: 30 s *acumulados* con el ladrón fijado. V15: el ladrón **se rinde** cuando un contador
   *continuo* llega a 20 s + 100 s × su reserva (≈ 117 s, porque casi no se cansa); el contador vuelve a cero cada vez que
   el dron pasa a buscar.
2. **Un mundo más duro.** Estatura variable (1.58-1.88 m), muros de 0.2 m de grosor, cansancio, civiles parecidos con
   cambios de ID.
3. **Errores de lógica** en las reglas nuevas.

Para separar 1 se mide la V15 también con el criterio de la V14 ("éxito táctico": llegar a 30 s fijado acumulados antes de
cualquier falla). Para separar 2 se repite la V15 con el **mundo de la V14** (estatura fija de 1.70 m, muros sin grosor,
ladrón sin cansancio, sin cambios de ID ni civiles parecidos), dejando toda la lógica nueva igual.

## Resultado

Los niveles se emparejan por contenido (la V15 agregó el "Duelo con civil" y separó el muro del muro con civil).

| Contenido | V14 · criterio V14 | V15 · criterio V14 | V15 mundo V14 · criterio V14 | V15 · rendición | V15 mundo V14 · rendición |
|---|---:|---:|---:|---:|---:|
| Duelo abierto (V14 N0, V15 N0) | 67 % ±3.3 (n 822) | **96 % ±2.5** (268) | 92 % ±3.4 (265) | 91 % ±3.6 | 86 % ±4.3 |
| Duelo con civil (solo V15 N1) | — | 89 % ±4.6 (187) | 92 % ±3.4 (239) | 45 % ±7.3 | **78 % ±5.4** |
| Muro (V14 N1, V15 N2) | 94 % ±1.9 (691) | **98 % ±2.2** (176) | 98 % ±2.0 (171) | 64 % ±7.2 | 70 % ±7.0 |
| Muro y civil (V14 N2, V15 N3) | 91 % ±2.3 (609) | **99 % ±1.7** (162) | 99 % ±1.2 (161) | 8 % ±4.3 | **17 % ±5.9** |
| Misión completa (V14 N3, V15 N4) | 62 % ±4.0 (591) | **92 % ±4.2** (171) | 90 % ±4.6 (175) | 14 % ±5.3 | 15 % ±5.4 |

Fallas de la V14 en la misión completa: alcanzado 12 %, perdido 12 %, peatón 7 %, panel 3 %. En la V15: alcanzado 5 %, no
encontrado 4 %, peatón 0-1 %, panel 0 %.

## Lectura

- **No hay errores de lógica que bajen el rendimiento.** Con el mismo criterio de éxito, la V15 es mejor que la V14 en
  todos los niveles comparables, y por más que el margen de ruido en el duelo abierto (+29 puntos) y la misión completa
  (+30 puntos). En muro y muro con civil también sube (+4 y +8), en el borde del ruido.
- **El mundo más duro casi no afecta el seguimiento**: con el criterio de la V14, V15 y V15 con mundo V14 están dentro del
  ruido en los 5 niveles.
- **La caída que se ve viene del criterio nuevo (la rendición).** En los niveles con muro casi todo lo que no es rendición
  es "5 min sin rendición" (no son fallas): el dron sigue al ladrón, pero el contador continuo de ~117 s se reinicia cada
  vez que el ladrón se esconde y el dron busca.
- Lo único del mundo nuevo que pesa sobre la rendición son **los civiles parecidos y los cambios de ID**: en el duelo con
  civil la rendición pasa de 45 % a 78 % al quitarlos, y en muro con civil de 8 % a 17 %. Cada duda de identidad pausa el
  contador (RECONFIRMAR) y, si el dron sigue a la persona equivocada, no cuenta.
- Las dos palancas para la rendición ya están en la decisión abierta **D-041**: que el ladrón se canse de verdad (hoy
  termina con 0.96-0.97 de reserva) y la frecuencia y el parecido del civil distractor. Entrenar debería mejorar también
  el contador, porque la red recibe la recompensa por la rendición.

## Cómo se midió

Scripts de medición en la carpeta temporal de la sesión (`medir_b.py`: entorno, etiqueta, nivel y código opcional para
cambiar constantes). El mundo V14 dentro de la V15 se armó con
`ESTATURA_MEDIA = 1.70, ESTATURA_SD = 0, GROSOR_MURO = 0, VC_LADRON = 99, P_CAMBIO = 0, SIM_CIVIL = (0.2, 0.2)`.
La línea base V14 corre el `entorno.py`, `control.py` y `mision.py` de la V14 (copias `*_v14.py`).
