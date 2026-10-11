# V15 · Fase E · Éxito por rendición, currículo de 5 niveles y visor

Fecha: 2026-10-10. Plan: `docs/PLAN_V15_CURRICULO.md` (secciones 2, 3, 5 y fase E). Medido con el último modelo de la
V14 **sin reentrenar**. **No se lanzó el entrenamiento** (espera la confirmación de Brahian).

## Qué se hizo

**`entorno.py`**
- **Rendición (D3):** contador continuo que suma con el ladrón (el de verdad) fijado y a la vista; se **pausa** sin
  verlo mientras el dron todavía sabe dónde está (memoria del tracker, PÉRDIDA, RECONFIRMAR) y **vuelve a cero** al pasar a
  la búsqueda (flanqueo, giros, siguiente obstáculo, altura, muro de canto). Se rinde a los **20 s + 100 s × reserva**. Es el
  éxito de la misión (reemplaza los 30 s acumulados). Tope de **5 min** (`PASOS_EPISODIO` 3000); sin rendición gana el ladrón.
- **5 niveles (D1):** 0 duelo abierto (sin muros ni civiles; huida en zigzag + 30 % cenit; arranca ya fijado), 1 duelo
  con civil (+ civil que cruza la línea de vista; arranca fijado), 2 muro, 3 muro y civil, 4 misión completa (**3-4 muros**,
  0-2 civiles, ladrón táctico o aprendido). `N_PANELES` = 4 (los que sobran se superponen). La red del ladrón congelado
  observa sus **2 muros más cercanos** (sigue con 22 entradas).
- **Ataques desde el nivel 2 (D6):** en los niveles 0 y 1 el ladrón no ataca ni salta (el cenit busca el punto ciego sin atacar).
- **Guardas nuevas** (necesarias con partidas de 5 min): **geocerca tipo ArduPilot** (FENCE + AVOID: frena con la
  deceleración real medida de la cascada, 1.5 m/s² y 0.5 s de retardo; en el nivel 0 la geocerca bajó de 21 % a **0 %**) y
  **personas recordadas** (no se acerca a < 2.5 m de alguien visto hace < 3 s, aunque esté a la espalda de la cámara: los
  choques con el civil del nivel 1 bajaron de 22 % a 3-4 %).

**`entrenar_master.py`** (V15, sale de `modelos_v14/`, guarda en `modelos_v15/`, arranca en el nivel 0)
- Criterios por nivel sobre las últimas 1000 partidas del nivel: 0 → rendición ≥ 85 % y cenit ≥ 70 % (el cenit cuenta);
  1 → rendición ≥ 85 %, ID correcto ≥ 98 %, 0 cambios sin detectar, 0 choques; 2 → rendición ≥ 80 % y re-adquisición
  media < 8 s; 3 → rendición ≥ 75 % e ID correcto ≥ 98 %; 4 → final. Mínimo 2 M pasos por nivel, paciencia 50 M, repaso 25 %.
- Competencia: sin rendición en 5 min = victoria del ladrón.
- Grabación: `replay_nivel_K.json` del nivel actual y la misión cada 5 iteraciones; los niveles ya superados, uno por
  turno; hitos del nivel actual cada 5 iteraciones durante sus primeras 50 y después cada 20 (`hitos/nivelK_itNNNNN.json`).

**`index.html`** (sin cambiar el diseño; copia previa `index_v17.html`)
- Selector: "Nivel K · … · en vivo (it N)" por nivel ("aún no entrenado" si falta), "Misión completa (despegue) · en
  vivo" e hitos agrupados por nivel. Con los archivos de la V14 queda como antes (probado).
- Panel de búsqueda: estados nuevos (RECONFIRMAR, MURO DE CANTO), **seguimiento continuo** con barra y **SE RINDE**,
  **pulso y reserva** del ladrón, **confianza del ID**; eventos de reconfirmación, "no es él", canto y rendición.
- **Nube de probabilidad** en el minimapa SLAM y en el piso 3D; punto de canto en el minimapa. Barra de dominio con N0-N4.

## Números (modelo V14 sin reentrenar; 160 entornos × 320 s por nivel)

| Nivel | Rinde | Sin rendición (5 min) | Perdido | Alcanzado | Panel | Peatón | Geocerca | Contador máx. medio |
|---|---|---|---|---|---|---|---|---|
| 0 Duelo abierto | **92 %** | 2 % | 6 % | 0 % | 0 % | 0 % | 0 % | 110 s |
| 1 Duelo con civil | 45 % | 26 % | 26 % | 0 % | 0 % | 3 % | 0 % | 85 s |
| 2 Muro | 59 % | 25 % | 0 % | 2 % | 14 % | 0 % | 0 % | 91 s |
| 3 Muro y civil | **5 %** | 74 % | 0 % | 4 % | 13 % | 3 % | 0 % | 35 s |
| 4 Misión completa | 8 % | 43 % | 0 % | 23 % | 14 % | 11 % | 0 % | 32 s |

(Todo con el código final, guardas de geocerca y de personas incluidas.)

Escenarios fijos (táctica: éxito = 30 s seguidos a la vista): abierto 100 %, cambio brusco 98 %, tras muro 100 %
(9.6-10.1 s de re-adquisición), detrás de la punta 96 %, cambia de lado 100 %, **debajo 82 %**.

## Lo que los números dicen y hay que decidir (no se forzó)

1. **El ladrón casi no se cansa** (reserva al final 0.96-0.97 en todos los niveles). Con velocidad crítica 3.0 m/s y
   carreras de 3.0-3.4 m/s apenas gasta, y escondido se recupera. Entonces T_rinde ≈ 117 s siempre: con un ladrón que se
   esconde, la rendición exige casi 2 minutos seguidos sin que se esconda nunca. **Decisión:** bajar la velocidad crítica
   (2.5 m/s, adulto sedentario) y/o D′ (100-120 m), hacer que la tensión gaste reserva, o aceptar que en los niveles con
   muro la rendición sea rara al principio (la paciencia de 50 M hará subir de nivel igual).
2. **El civil distractor es muy insistente:** cruza la línea de vista una y otra vez → ~16 reconfirmaciones por misión de
   5 min en el nivel 1 (cada una pausa el contador 1-2 s). Es mucha carga para un operador real. **Decisión:** que cruce
   menos (cada 15-30 s) o que solo algunos civiles sean distractores.
3. **Choques con muros en partidas largas:** 13-14 % por partida en los niveles 2-4 (las partidas ahora duran ~3-4 min).
   No subieron por minuto, pero con 5 min pesan más.
4. Con 0 cambios de ID sin detectar en 1 556 partidas del nivel 1 y el ID correcto el 96 % del tiempo, el criterio "ID
   correcto ≥ 98 %" depende de que el entrenamiento aprenda a evitar los cruces.

## Criterio de aceptación de la fase E
- Las 6 pestañas cargan: **sí** (5 niveles + misión; probado con el ensayo de entrenamiento y con los archivos de la V14).
- El nivel se guarda y se retoma: **sí** (`estado_entrenamiento.json` guarda `current_level`, `pasos_inicio_nivel` e
  historial; el mismo comando retoma `modelos_v15/ultimo.zip`).

## Pruebas
61 pasan. Nuevas (`TestFaseE`): el contador se pausa en PÉRDIDA, vuelve a cero al pasar a la búsqueda y la rendición es
el éxito; tope de 5 min; los 5 niveles (muros, civiles, arranque fijado, 22 entradas del ladrón); sin ataques ni saltos en
los niveles 0 y 1; criterios del currículo (un solo cambio sin detectar bloquea el nivel 1). Se actualizaron las pruebas de
la V13 y la V14 que describían el currículo viejo de 4 niveles.

---

## Anexo · salida de herramientas/evaluar_politica.py (entorno V15, éxito táctico = 30 s seguidos)

### Evaluación en escenarios fijos · v15-fase-E

Modelo: `..\..\..\..\AppData\Local\Temp\claude\C--Users-Brahi-Desktop-Claude\acb305c0-ec86-4acf-8f4d-4a0cb137aa56\scratchpad\v14_ultimo.zip`

Política determinista · 50 partidas por escenario · semillas 0.. · nivel de currículo 0.10 · máx. 120 s · 2026-10-10 16:33

## Resultados por escenario

| Escenario | Cumplida | Perdido | Alcanzado | Panel | Geocerca | Tiempo agotado | Duración (s) | A la vista | Pérdidas | Re-adquiere | t re-adq. (s) | Dist. mín. (m) | Altura máx. (m) | Gimbal mín/máx (°) | Recompensa | de ella, control | Jitter cabeceo (°/paso) | Jitter yaw (°/s/paso) | Jitter gimbal (°/s/paso) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| abierto | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 31.5 | 0.97 | 0.04 | 0.04 | 0.1 | 4.7 | 3.1 | -45 / 11 | 14.1 | -0.7 | 2.85 | 0.95 | 4.39 |
| cambio_brusco | 0.98 | 0.00 | 0.02 | 0.00 | 0.00 | 0.00 | 33.8 | 0.90 | 1.94 | 1.94 | 0.8 | 1.6 | 4.9 | -45 / 7 | 14.4 | -0.2 | 1.29 | 1.35 | 2.86 |
| tras_muro | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 48.6 | 0.74 | 1.14 | 1.14 | 10.1 | 3.1 | 4.3 | -45 / 2 | 17.9 | -0.2 | 0.46 | 0.43 | 1.25 |
| detras_punta | 0.96 | 0.00 | 0.00 | 0.00 | 0.00 | 0.04 | 52.4 | 0.75 | 1.54 | 1.52 | 9.0 | 3.3 | 3.5 | -45 / 8 | 16.6 | -0.2 | 0.65 | 0.60 | 1.30 |
| cambia_lado | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 45.3 | 0.80 | 1.10 | 1.10 | 7.4 | 3.4 | 3.7 | -45 / 4 | 16.5 | -0.1 | 0.39 | 0.52 | 1.09 |
| debajo | 0.82 | 0.18 | 0.00 | 0.00 | 0.00 | 0.00 | 46.5 | 0.72 | 2.94 | 2.76 | 1.1 | 1.8 | 5.6 | -45 / -0 | 10.8 | -0.0 | 2.26 | 4.63 | 3.46 |

Acciones elegidas con la IA al mando (fracción):

| Escenario | MANTENER | EVADIR_IZQ | EVADIR_DER | DETENER_ASCENDER | GIRAR_IZQ | GIRAR_DER | AVANZAR | DESCENDER | GIMBAL_ARRIBA | GIMBAL_ABAJO |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| abierto | 0.01 | 0.01 | 0.15 | 0.09 | 0.21 | 0.32 | 0.05 | 0.06 | 0.03 | 0.05 |
| cambio_brusco | 0.09 | 0.02 | 0.20 | 0.05 | 0.18 | 0.22 | 0.02 | 0.10 | 0.05 | 0.08 |
| tras_muro | 0.21 | 0.18 | 0.06 | 0.02 | 0.02 | 0.05 | 0.01 | 0.06 | 0.11 | 0.28 |
| detras_punta | 0.29 | 0.03 | 0.05 | 0.03 | 0.03 | 0.13 | 0.01 | 0.14 | 0.20 | 0.09 |
| cambia_lado | 0.08 | 0.14 | 0.06 | 0.02 | 0.28 | 0.11 | 0.00 | 0.08 | 0.13 | 0.10 |
| debajo | 0.16 | 0.03 | 0.05 | 0.01 | 0.08 | 0.13 | 0.00 | 0.12 | 0.11 | 0.32 |
