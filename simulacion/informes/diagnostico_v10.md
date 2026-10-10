# Diagnóstico · V10 master (0 → 767 M pasos)

Fuentes: `resumen_v10-master-767M.md`, `resumen_v10-master-350M.md`, `barrido_v10-master.md` (32 modelos × 4
escenarios × 50 partidas) y `evaluacion_v10-763M-con-reglas-v11.md` (el último modelo con el código v11: gimbal
-45°, `PERDIDA_IA = False`). Fecha: 2026-10-10.

## 1. Qué muestran los números

| Medida | Valor | Lectura |
|---|---|---|
| Cumplida (entrenamiento) | 32 % → 25 % (150-250 M) → 31 % hoy | 767 M pasos sin superar el arranque desde la v9 |
| Perdido / alcanzado | 45 % / 14 % | La pérdida del objetivo es la falla dominante |
| Entropía | 1.41 → 1.58-1.61 (máx. 2.30), plana desde 100 M | La política no se volvió más decidida |
| Castigo de control vs recompensa | -7.8 vs total -7.3 por partida | Todo lo demás junto aporta apenas +0.5 |
| Acciones en la búsqueda por IA | GIRAR 0 %, AVANZAR 0 % (los 767 M) | Se queda casi quieta: solo re-adquiere si el ladrón vuelve solo al cuadro |
| Escenarios fijos, v10 (búsqueda IA) | abierto 100 %, cambio brusco 0 %, tras muro 0 %, debajo 0-20 % | Idéntico en los 32 modelos: el entrenamiento no cambió nada de esto |
| Mismo modelo con reglas v11 | abierto 100 %, cambio brusco **60 %**, tras muro **94 %**, debajo 0 % | El protocolo determinista re-adquiere (0.7-1.0 por partida, en ~10-12 s) |
| "Debajo" a lo largo del entrenamiento | 25-50 M: alcanzado 88 %, a la vista 82 %. Desde 75 M: alcanzado 0 %, sube a 4.3 m, a la vista 3-6 %, perdido 96 % | Aprendió a sobrevivir al salto subiendo, a costa de perder al ladrón |
| Jitter (persecución en abierto) | cabeceo 3.1 °/paso, gimbal 4.5 °/s/paso, castigo de control -19 por partida | El escenario más limpio es el que más castiga |

**Mejoró:** sobrevivir al ladrón que salta (alcanzado en "debajo" 88 % → 0 % desde 75 M). El jitter de la
corrida bajó de 0.051 a 0.043-0.047 Σ|Δu|/paso.
**Empeoró o no avanzó:** cumplida, perdido, entropía y la búsqueda por IA. Quedó estancado durante 767 M pasos.

## 2. Hipótesis (honestas)

- **Búsqueda congelada.** El 0 % de GIRAR y AVANZAR está confirmado. La causa probable es el reparto de la
  recompensa: en `BUSQUEDA_IA` la única recompensa es +3 al re-adquirir, que llega pocas veces. Mientras tanto,
  el castigo de esfuerzo (0.03·Σ|u|) y el de derivada se cobran en cada paso, así que moverse sale caro y quedarse
  quieto es lo más barato. **No se puede comprobar** sin la recompensa por componente, que no se registra. Con
  `PERDIDA_IA = False` el problema deja de aplicar en la v11.
- **El castigo de control cae sobre canales que la red no maneja.** Con el objetivo fijado y visible, la
  guiñada (`tasa_t`) y el gimbal (`gmb_corrige`, KP 4) los decide el seguimiento determinista. Las acciones
  GIMBAL_* no tienen efecto en FIJADO. Aun así, `u` y su multa incluyen esos canales. En "abierto" la red
  elige casi siempre acciones sin efecto (GIRAR con el objetivo a la vista, EVADIR sin amenaza) y paga -19 por
  partida. Es ruido en el retorno que no depende de sus acciones.
- **El gimbal en -46° / -48° (v10)** era `cam_pitch` = ángulo del gimbal + error de estabilización por el
  cabeceo del chasis, con el límite de entonces en -60°. Lo comandaba el seguimiento determinista, no la red.
  En la v11 el recorte de -45° se aplica en `entorno.py` y en `control.GimbalBaseCam`, y lo validan las pruebas
  (la evaluación con reglas v11 da mínimo -45°).
- **"Debajo" es un punto ciego geométrico.** Con el gimbal en -45° y VFOV 29.7°, el borde inferior de la imagen
  mira a -59.9°. A 5.3 m de altura, una persona a menos de ~2.2 m en horizontal no cabe en el cuadro. El
  retroceso (`v_rango = -0.6` a < `R_RETROCEDE` 2.5 m) solo actúa si hay persecución (`persigue`: AVANZAR o
  aproximación a > 10 m). Como la red casi nunca elige AVANZAR, el dron sube pero no se aparta.

## 3. Cambios propuestos (máximo 3, compatibles con las reglas duras v11)

**C1 · Separación mínima automática según la altura (escenario "debajo").**
- Hipótesis: si el dron se aparta lo suficiente para que el ladrón quede dentro del cuadro con el gimbal en
  -45°, no lo pierde y tampoco queda al alcance del salto.
- Dónde: `entorno.py`, `EntornoDronPersona.step`, bloque de consignas de velocidad (`persigue`, `v_rango`).
- Cambio exacto:
  - Con el objetivo fijado y visible (`decide & ve`), el retroceso deja de depender de AVANZAR:
    `persigue |= decide & ve & (d_obj < r_min)`.
  - La distancia mínima pasa a depender de la altura:
    `r_min = max(R_RETROCEDE, (dz - 0.9) / tan(radians(-GIMBAL_MIN + VFOV/2)) + 1.0)`.
  - La velocidad de retroceso sube de -0.6 a -1.5 m/s.
- Métrica: escenario "debajo". Cumplida pasa de 0 % a **≥ 30 %**, a la vista de 11 % a ≥ 40 % y alcanzado ≤ 5 %.
  "abierto" se mantiene en 100 % y la geocerca en ≤ 2 %.

**C2 · Multar a la red solo por lo que ella comanda.**
- Hipótesis: quitar del castigo los canales deterministas baja la varianza del retorno sin cambiar el
  comportamiento físico.
- Dónde: `entorno.py`, `step`, bloque "suavidad del control".
- Cambio exacto: antes de `pen_delta` y `pen_esfuerzo`, enmascarar `u`:
  - Guiñada en 0 si `ve` (la sigue el seguimiento determinista).
  - Gimbal en 0 si `fij` (la red no lo mueve en FIJADO).
  - El cabeceo queda igual.
  - El jitter físico se sigue midiendo aparte, con la `u` completa.
- Métrica: "abierto", el castigo de control pasa de -19 a **≥ -8** por partida, sin bajar la cumplida (100 %) y
  sin subir el jitter de cabeceo más de 10 %. En el entrenamiento, la entropía debería bajar de 1.58.

**C3 · Registrar lo que hoy falta, antes de reentrenar.**
- Hipótesis: sin la recompensa por componente no se puede probar ni descartar la causa del estancamiento.
- Dónde:
  - `entorno.py`, `step`: `info["r_comp"]`, con los términos vista, rango, guía, descubre, pierde, maniobra,
    éxito, fallas y control, y `info["du"]`, con |Δu| por eje.
  - `entrenar_master.py`, `VecDron.step_wait` y `resumen()`: duración de la partida, recompensa por componente,
    jitter por eje, `min(cam_pitch)` y recuperaciones (`recupera`, que con la búsqueda determinista reemplaza
    a `descubre`).
- Métrica: `resumir_metricas.py` ya no lista nada en "Lo que no se registra" (salvo TensorBoard, opcional). Las
  pruebas siguen pasando.

## 4. Lo que no se puede saber con estos datos

- La recompensa por componente durante el entrenamiento (solo se separa el control).
- Cómo aprendería la red con las reglas v11. Lo de arriba es la política v10 evaluada con el código v11, sin
  reentrenar: su observación todavía trae entradas de la búsqueda por IA que ahora siempre valen 0.
- Si los escenarios fijos representan bien al ladrón táctico. Allí el ladrón sigue rutas impuestas, salta en
  "debajo" y no hay peatones.

Recomendación de orden: C3 → C1 → C2 → reentrenar con las reglas v11 → volver a pasar este ciclo.
