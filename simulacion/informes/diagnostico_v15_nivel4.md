# Diagnóstico · V15, nivel 4 "Misión completa" (rendición estancada en 31-34 %)

Lo escribe el supervisor (sin tocar código). Fecha: 2026-10-10, ~23:00. Entrenamiento en 34.6 M pasos, 10.2 M en el
nivel 4.

**Fuentes:**
- `salida/estado.json` y la última entrada de `salida/metricas.json`.
- `docs/PLAN_V15_CURRICULO.md` y `docs/INFORME_JORNADA_2026-10-10.md`.
- `informes/evaluacion_v15-ajustes-D041.md`.
- Mediciones propias de solo lectura con `dron_master_34727424_steps.zip` en el nivel 4, sin repaso. Fueron 64
  partidas con la política estocástica, 64 y 128 con la determinista, y 64 con AVANZAR forzado (script temporal, no
  versionado).

## 1. Qué muestran los números

| Medida (nivel 4) | Valor | Lectura |
|---|---|---|
| Rendición (criterio del currículo, 1000 partidas) | 33 % | Plana desde que entró al nivel (10 M pasos) |
| Medición propia, determinista / estocástica | 36 % (64) · 27 % (128) / 33 % (64) | Mismo nivel: el azar de la política no es la causa. Ruido de ±6-8 puntos con estas muestras |
| Partidas que terminan por el tope de 5 min | 59-62 % | Es casi toda la falla. Perdido 0-4 %, no encontrado 3-8 %, alcanzado 0-2 % |
| En esas partidas: moral final / T_rinde | 0.30 (el piso) / **43 s** | La moral ya está saturada: re-encontrarlo más veces no acerca la rendición |
| En esas partidas: mejor racha del contador | mediana **25-27 s** | Le faltan ~16-18 s. Solo el 4-11 % llega al 80 % del umbral |
| En esas partidas: reinicios del contador | ~12 por partida | Cada 25 s el ladrón vuelve a cortar la línea de vista |
| En esas partidas: tiempo en búsqueda determinista | **150-160 s de 300** | ~13 s por pérdida. El criterio del nivel 2 pedía < 8 s |
| Vista acumulada en 5 min (todas) | mediana 94 s · 84 % de las partidas ≥ 60 s · 53 % ≥ 90 s | El dron sí mantiene la custodia buena parte del tiempo |
| Reserva del ladrón al final | 0.75-0.90 | Escondido descansa: el cansancio casi no actúa en 5 min |
| Entropía de la política | 1.91 (máx. 2.30) | Más alta que en la V10 (1.58): la red está cerca del azar porque sus acciones casi no cambian el resultado |
| Recompensa por partida (mezcla de niveles) | vista +32, descubre +81, pierde -83, éxito **+2.2** | La rendición pesa 15 veces menos que mirar |

**Qué controla la red en el nivel 4.**
- Solo decide en FIJADO. Con el ladrón a la vista, su única palanca real es AVANZAR (persecución predictiva a
  3.5-5 m) y la maniobra ante una amenaza. La búsqueda es determinista (regla 3) y la altura en FIJADO es fija (3.30 m).
- AVANZAR casi no se usa (0.02 %). **Lo probé forzándolo** cuando lo ve a más de 5.5 m: la rendición cae de 36 % a
  **9 %** y no encontrado sube a 11 %. Acercarse lo hace esconderse antes. Evitar AVANZAR es correcto, no un fallo de
  exploración.
- Conclusión: **el techo de ~33 % lo ponen el entorno y el criterio, no la red.** Por eso 10 M pasos no lo mueven, y
  el 37 % del modelo V14 sin reentrenar está dentro del ruido.

## 2. Por qué no sube la rendición

1. **El contador vuelve a cero en cada búsqueda.** Con 3-4 muros el ladrón táctico siempre tiene cubierta cerca y
   corta la línea de vista cada ~25 s. La búsqueda determinista tarda ~13 s en devolverlo, y aunque lo encuentre en 2 s
   (un rodeo corto de MURO_DE_CANTO) el contador ya se borró. Para rendirse necesita ~43 s seguidos y la mejor racha
   mediana es 25 s.
2. **La moral ya no ayuda.** Llega a su piso (0.3) tras ~5-6 re-encuentros, antes de la mitad de la partida. Desde ahí
   T_rinde queda fijo en ~43 s. Bajar el piso casi no cambia nada: con las mismas trayectorias, 0.20 da 32 % y 0.15
   da 35 % (base 27 %).
3. **La recompensa no empuja hacia la rendición.**
   - Al tope de 5 min, `entrenar_master.py` marca la partida como `TimeLimit.truncated`. SB3 la trata como si
     siguiera (bootstrap del valor), así que **perder por tiempo no le cuesta nada**.
   - `R_EXITO = 5` es menos de lo que el dron cobraría en `R_VISTA + R_RANGO` si siguiera mirando el resto de la
     partida. Rendirlo temprano le resta recompensa.
   - El dron tampoco observa el tiempo que lleva la partida. Es un problema real, pero de segundo orden mientras la
     red tenga tan poca palanca.

## 3. ¿El nivel 4 es razonable para el caso de uso policial?

- El trabajo del dron en el caso policial es **la custodia**: no perder al sospechoso, o re-encontrarlo rápido, hasta
  que llegue la patrulla. Que una persona escondida entre 3-4 muros "se rinda" por el dron es una regla del juego que
  sirve para entrenar y para la narrativa, pero no es lo que se le pediría a un sistema real.
- Además, en el simulador el ladrón casi no se cansa (escondido recupera la reserva: 0.8 al final), así que la
  rendición depende casi solo del contador continuo.
- Con 3-4 muros y el contador que se reinicia en cada búsqueda, el 33 % mide sobre todo la geometría y la táctica del
  ladrón, no al dron.
- El plan ya dice que el nivel 4 es "nivel final: solo se reporta". El estancamiento no bloquea el currículo, pero el
  número que se reporte para el proyecto de grado debería ser el operativo.

## 4. Cambios propuestos (máximo 3; todos dentro de las reglas duras)

**C1 · Contador: pausa en vez de reinicio si lo re-encuentra rápido** (lo decide Brahian: modifica D3).
- Hipótesis: un rodeo corto no significa que el dron "ya no sabe dónde está". Si lo re-adquiere en ≤ 8 s (el mismo
  estándar del criterio del nivel 2), el contador debería pausarse, no borrarse.
- Dónde: `entorno.py`, `EntornoDronPersona.step`, cálculo de `t_cont` y `reinicia`.
- Cambio exacto:
  - Llevar `t_en_busqueda`: cero al salir a FIJADO, suma `DT` en los estados de `reinicia`.
  - Reiniciar `t_cont` solo si `t_en_busqueda > T_PAUSA_REID = 8.0`. Mientras tanto se pausa.
  - Nada más cambia: T_rinde, moral, tope ni recompensas.
- Métrica: rendición en el nivel 4 de **≥ 45 %** con 128 partidas deterministas (contrafactual medido sobre las mismas
  trayectorias: 27 % → **47 %**; con 5 s, 33 %; con 12 s, 62 %). Los niveles 0-3 no bajan más de 5 puntos. Las fallas
  (perdido, alcanzado, choques) no suben.
- Reportar además la **custodia**: vista acumulada ≥ 60 s en 5 min y nunca "perdido". Hoy da 84 % a 60 s y 53 % a 90 s.
  Es la métrica operativa del caso policial.

**C2 · Que la recompensa sí prefiera la rendición.**
- Hipótesis: con el tope gratis y el éxito más barato que seguir mirando, el crítico no distingue ganar de dejar correr
  el reloj. Esto ensucia cualquier mejora futura.
- Dónde: `entrenar_master.py`, `VecDron.step_wait` (`TimeLimit.truncated`), y `entorno.py`, `step` (`rc["exito"]`,
  `rc["fallas"]`).
- Cambio exacto:
  - En los niveles con rendición, el tope de 5 min sin rendición es **terminal** (`truncated = False`) y cobra
    `R_TOPE = -5` en `rc["fallas"]`.
  - `R_EXITO = 5 + 0.25 × segundos restantes` (0.25/s ≈ lo que cobra mirando con ~50 % de vista), así que rendirlo
    antes nunca vale menos que seguir mirando.
- Métrica: entropía < 1.75 en 10 M pasos. Rendición en el nivel 4 a **+5 puntos** sobre la base medida con la misma
  evaluación. Fallas sin cambio (± 1 punto).
- Honesto: el efecto esperado es pequeño mientras la red tenga poca palanca (punto 1). Se propone porque es una
  incoherencia que conviene corregir antes del próximo entrenamiento largo.

**C3 · Medir por nivel y por estado de búsqueda dónde se van los 13 s de cada re-adquisición.**
- Hipótesis: la palanca grande que queda dentro de la regla 3 es la búsqueda determinista (150-160 s de 300 en las
  partidas que pierden por tiempo). Sin saber qué estado se lleva el tiempo, no se puede proponer un cambio exacto.
  FLANQUEO_PROFUNDO es el 21 % del tiempo total en la mezcla de niveles.
- Dónde: `entrenar_master.py` (`VecDron.fin_x` y el resumen por nivel) y `herramientas/resumir_metricas.py`.
- Cambio exacto: por partida y por nivel, guardar:
  - tiempo en cada estado de búsqueda;
  - qué estado terminó en re-adquisición;
  - tiempo hasta re-adquirir;
  - mejor racha del contador;
  - T_rinde final.
  Tabla por nivel en el resumen.
- Métrica: el resumen muestra esa tabla para el nivel 4. Meta para el siguiente ciclo: re-adquisición media en el
  nivel 4 de 13 s a **≤ 8 s**.

## 5. Qué no haría (y por qué)

- **Forzar o premiar AVANZAR:** medido, 36 % → 9 %.
- **Bajar `MORAL_MIN`:** contrafactual de 27 % → 32-35 %. Mueve la meta sin mejorar al dron.
- **Inflar el cansancio para que el ladrón se rinda solo:** mismo problema. Además ya se descartó en D-041 por
  fisiología.
- **Seguir entrenando igual:** 10 M pasos planos y entropía alta. Sin C1-C3 no hay señal que aprender.

## 6. Lo que no se puede saber con estos datos

- El desglose del nivel 4 dentro de `metricas.json`: mezcla un 25 % de repaso de niveles 0-3. Por eso medí aparte.
- El efecto real de C1 y C2 cuando el ladrón y el dron reaccionan al cambio. Los contrafactuales usan las mismas
  trayectorias, así que son una estimación, no una garantía.
- Cuánto de los ~13 s por re-adquisición es inevitable con 3-4 muros (falta C3).
