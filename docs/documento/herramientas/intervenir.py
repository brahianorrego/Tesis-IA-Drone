"""Genera la copia intervenida del Word del proyecto de grado.

Rojo: sobra o está mal. Amarillo: texto nuevo. Verde: reemplaza al rojo que tiene justo antes.
Turquesa: [REVISAR: ...] decisiones de Brahian.
"""
import re
import sys

from helpers import (nota_after, AMARILLO, LOG, ROJO, TURQ, VERDE, Doc, add_text, figura_after, insertar_tras, marcar,
                     par_after, par_before, reemplazar, revisar, tabla_after, titulo_fig)

ENTRADA, SALIDA, DIAG = sys.argv[1], sys.argv[2], sys.argv[3]
D = Doc(ENTRADA)
P = D.P
f = D.find
T_ORIG = list(D.d.tables)
import copy as _copy
LISTA_PPR = P[188]._p.pPr


def rev_after(p, nota):
    return par_after(D, p, f'[REVISAR: {nota}]', TURQ, copiar_formato=False)


def li_after(last, texto):
    para = par_after(D, last, '', AMARILLO, copiar_formato=False)
    if para._p.pPr is not None:
        para._p.remove(para._p.pPr)
    para._p.insert(0, _copy.deepcopy(LISTA_PPR))
    from helpers import add_text as _at
    _at(para, texto, AMARILLO)
    return para


def seq(anchor, items):
    """Inserta en orden una lista de bloques después de `anchor`. Devuelve el último."""
    last = anchor
    for it in items:
        tipo = it[0]
        if tipo == 'h2':
            last = par_after(D, last, it[1], AMARILLO, style='Heading 2')
        elif tipo == 'h3':
            last = par_after(D, last, it[1], AMARILLO, style='Heading 3')
        elif tipo == 'p':
            last = par_after(D, last, it[1], AMARILLO, copiar_formato=False)
        elif tipo == 'pv':
            last = par_after(D, last, it[1], VERDE, copiar_formato=False)
        elif tipo == 'li':
            last = li_after(last, it[1])
        elif tipo == 'rev':
            last = par_after(D, last, f'[REVISAR: {it[1]}]', TURQ, copiar_formato=False)
        elif tipo == 'tabla':
            _, etq, tit, filas, anchos = it[:5]
            nota = it[5] if len(it) > 5 else None
            cap = titulo_fig(D, last, etq, tit)
            tbl = tabla_after(D, cap._p, filas, anchos)
            last = nota_after(D, tbl, nota) if nota else par_after(D, tbl, '', AMARILLO, style='Normal')
        elif tipo == 'fig':
            _, etq, tit, img, nota = it
            cap = titulo_fig(D, last, etq, tit)
            fig = figura_after(D, cap, img)
            last = nota_after(D, fig, nota) if nota else par_after(D, fig, '', AMARILLO, style='Normal')
    return last


# =====================================================================
# 0. Leyenda
# =====================================================================
leyenda = [
    'COPIA INTERVENIDA DEL DOCUMENTO · 12 de octubre de 2026',
    'Cómo leer esta copia: lo resaltado en ROJO sobra o está mal; lo resaltado en AMARILLO es texto nuevo; lo '
    'resaltado en VERDE reemplaza al texto rojo que tiene justo antes; lo resaltado en TURQUESA son decisiones que '
    'debe tomar Brahian ([REVISAR: ...]).',
    'Fuentes de los datos: carta al comité del 01/09/2026; repositorio Tesis-IA-Drone, ramas v15-curriculo y '
    'v16-simulacion (docs/PLAN_MINIMO_FISICO.md, docs/hardware.md, docs/pixhawk.md, docs/jetson.md, '
    'docs/DECISIONES.md) e informes simulacion/informes/minimo_tesis_protocolo.md y minimo_tesis_decisor_ia.md. '
    'Las pruebas estadísticas nuevas (Wilson y McNemar) se calcularon con minimo_tesis_decisor_ia.csv. La ficha de '
    'hechos, la guía y los diagramas están en docs/documento/ del repositorio.',
    'Para cerrar la intervención: borrar todo lo rojo, quitar el resaltado de lo verde y lo amarillo, resolver lo '
    'turquesa, actualizar los índices (clic derecho sobre cada índice > Actualizar campo > Actualizar toda la tabla) '
    'y borrar esta leyenda. Las tablas y figuras nuevas se numeraron N1, N2…; hay que renumerarlas al final.',
    'Reglas de la plantilla USB que aplican a lo nuevo: los rótulos nuevos están escritos como texto; al aceptar '
    'hay que recrearlos con Referencias > Insertar título (Tabla o Figura) para que aparezcan en las listas. Si una '
    'tabla o figura es de autoría propia no hace falta la nota "Elaboración propia"; las notas van con "Nota" en '
    'cursiva y en 10 puntos. Las tablas llevan solo líneas horizontales y no deben quedar partidas entre páginas. El '
    'detalle de las 68 indicaciones de la plantilla está en docs/documento/GUIA_PROYECTO_DE_GRADO.md.',
]
ancla = P[0]
for i, t in enumerate(leyenda):
    par_before(D, ancla, t, AMARILLO, bold=(i == 0))

# =====================================================================
# 1. Preliminares
# =====================================================================
revisar(P[5], 'confirmar si Tania Sierra Galindo sigue como coautora. Si no, quitarla aquí y en el cuadro '
              '"Citar/How to cite"')
revisar(P[13], 'completar el título del magíster del asesor (el texto quedó cortado: "Magíster (MSc) en …")')
for p in P[:60]:
    if 'Seleccione grupo de investigación' in p.text or 'Seleccione línea de investigación' in p.text:
        revisar(p, 'elegir el grupo y la línea de investigación en la lista desplegable de la plantilla')
for t in ('Texto de dedicatoria centrado', 'Texto de agradecimientos centrado'):
    p = f(t)
    marcar(p)
    revisar(p, 'escribir el texto o quitar la página (APA 7 no la exige)')
rev_after(P[114], 'después de aceptar los cambios, actualizar las listas de tablas y '
        'figuras: hoy hay dos "Figura 28", la lista salta de la Figura 11 a la 15 y de la Tabla 13 a la 16')

# Resumen y abstract
p = f('Este trabajo presenta la implementación experimental')
reemplazar(D, p, 'una computadora acompañante embarcada para el procesamiento de la información',
           'una computadora de a bordo NVIDIA Jetson Orin Nano para el procesamiento de la información')
insertar_tras(p, 'cuando se presenta una condición de riesgo.',
              ' La decisión de intervenir la toma un clasificador de riesgo entrenado en simulación, dentro de reglas '
              'de seguridad.')
reemplazar(D, p, 'El aporte principal del trabajo consiste en demostrar la viabilidad de integrar percepción, decisión y '
           'control de vuelo en una plataforma académica real, bajo restricciones de procesamiento, sensado y seguridad '
           'operativa en vuelo al aire libre.', 'El aporte es mostrar que percepción, decisión y control pueden '
           'integrarse en una plataforma académica real que vuela al aire libre.')
reemplazar(D, p, 'con obstáculos tipo panel, referencia de posición satelital y registro de las condiciones ambientales '
           'del ensayo (iluminación natural y régimen de viento)', 'con obstáculos tipo panel y registro del viento y '
           'la iluminación de cada ensayo')
revisar(p, 'al terminar las pruebas de campo, agregar dos o tres frases con los resultados (tasa de éxito con su '
           'intervalo de confianza y latencia medida) y una conclusión. APA 7 pide un resumen de máximo 250 palabras')
p = f('This work presents the experimental implementation')
reemplazar(D, p, 'an onboard companion computer for information processing',
           'an onboard NVIDIA Jetson Orin Nano computer for information processing')
insertar_tras(p, 'whenever a risk condition is detected.',
              ' The decision to intervene is made by a risk classifier trained in simulation, inside safety rules.')
revisar(p, 'la plantilla pide no usar traductores automáticos: que una persona revise el abstract cuando el '
           'resumen esté final. Mismo largo que el resumen (150 a 250 palabras)')

# =====================================================================
# 2. Introducción, planteamiento y justificación
# =====================================================================
for p in P[150:400]:
    if 'Ahmed et al., 2022' in p.text:
        reemplazar(D, p, 'Ahmed et al., 2022', 'Kurunathan et al., 2024')
p = f('suele emplearse una Raspberry Pi como unidad')
reemplazar(D, p, 'una Raspberry Pi', 'una computadora acompañante (por ejemplo, una Raspberry Pi o una NVIDIA Jetson)')
p = f('una computadora acompañante como unidad de procesamiento, una controladora Pixhawk')
reemplazar(D, p, 'una computadora acompañante como unidad de procesamiento',
           'una computadora de a bordo NVIDIA Jetson Orin Nano como unidad de procesamiento')
insertar_tras(p, 'como apoyo para la identificación de obstrucciones.',
              ' La decisión de intervenir no depende solo de umbrales fijos: la toma un clasificador aprendido que '
              'opera dentro de reglas de seguridad, y el capítulo 2 compara ambos enfoques con los mismos escenarios.')
p = f('proyecto utiliza una Raspberry Pi como unidad de procesamiento')
reemplazar(D, p, 'una Raspberry Pi como unidad de procesamiento',
           'una computadora NVIDIA Jetson Orin Nano como unidad de procesamiento')
reemplazar(D, p, 'a una respuesta básica de ascenso vertical', 'a una respuesta básica de detención y ascenso vertical')
p = f('El empleo de una Raspberry Pi como unidad de procesamiento')
reemplazar(D, p, 'El empleo de una Raspberry Pi', 'El empleo de una NVIDIA Jetson Orin Nano')
reemplazar(D, p, 'Mientras la Raspberry Pi procesa', 'Mientras la Jetson procesa')

# Objetivos: no se tocan
revisar(f('Implementar un sistema experimental de detección de personas y evasión', 170, 190),
        'los objetivos se dejan exactamente como los aprobó el comité; no se cambiaron')

# =====================================================================
# 3. Alcances y limitaciones
# =====================================================================
A = P[188:198]
reemplazar(D, A[0], 'la Raspberry Pi', 'la computadora de a bordo (NVIDIA Jetson Orin Nano)')
reemplazar(D, A[1], 'la Raspberry Pi,', 'la computadora de a bordo NVIDIA Jetson Orin Nano,')
marcar(A[3])
par_after(D, A[3], 'Se implementará en la computadora de a bordo (NVIDIA Jetson Orin Nano) el módulo de '
          'percepción–decisión, integrando el detector de personas con una lógica de evasión básica basada en reglas '
          'y estados, dentro de la cual un clasificador de riesgo entrenado (perceptrón multicapa) decide cuándo '
          'intervenir; las reglas de seguridad conservan siempre la prioridad.', VERDE)
reemplazar(D, A[4], 'respuesta,', 'respuesta.')
reemplazar(D, A[6], 'la Raspberry Pi y la Pixhawk', 'la Jetson Orin Nano y la Pixhawk')
reemplazar(D, A[8], 'frente a obstáculos fijos ubicados en la trayectoria de avance',
           'frente a obstáculos fijos y a personas (primero con un maniquí) ubicados en la trayectoria de avance o '
           'cerca de ella')
revisar(A[8], 'ajuste menor: el protocolo incluye personas porque así lo pide el objetivo general')
nuevo = par_after(D, A[9], 'Como apoyo a la validación de campo, el mismo protocolo se reproducirá en una simulación '
                  'del sistema (sensores con ruido y retardo, y modelo del control de ArduPilot), que permite repetir '
                  'cada escenario muchas veces y comparar la decisión basada solo en reglas con la decisión del '
                  'clasificador.', AMARILLO)
revisar(nuevo, 'alcance nuevo; respalda los vuelos simulados del capítulo 3. Si el asesor prefiere no agregar '
               'alcances, mover este texto a 2.3 como instrumento complementario')

L = P[199:209]
marcar(L[0])
par_after(D, L[0], 'El detector de personas no se entrenará desde cero: se usará un modelo YOLO preentrenado en COCO, '
          'por lo que su desempeño dependerá de la cobertura y las características de ese conjunto de datos. El único '
          'componente que se entrena dentro del proyecto es el clasificador de decisión, una red pequeña (perceptrón '
          'multicapa de 15 entradas) que no procesa imágenes y se entrena con datos de simulación etiquetados de forma '
          'automática.', VERDE)
marcar(L[2])
par_after(D, L[2], 'Como criterio de delimitación, la arquitectura se basa en la cámara frontal, el sensor LiDAR de '
          'proximidad frontal, la computadora de a bordo NVIDIA Jetson Orin Nano y la controladora Pixhawk. Los '
          'elementos propios de la plataforma de vuelo, como el receptor GPS de la controladora (que el modo GUIDED '
          'exige en exteriores) y el estabilizador de cámara de dos ejes con inclinación fija, no aportan entradas '
          'nuevas a la lógica de decisión. No se integrarán sensores adicionales de percepción, como otros LiDAR, '
          'radares o cámaras de profundidad.', VERDE)
marcar(L[4])
par_after(D, L[4], 'La validación en campo se hará con un número limitado de repeticiones por escenario (diez), por lo '
          'que la tasa de éxito de campo se reportará con su intervalo de confianza y se complementará con la '
          'evaluación del mismo protocolo en simulación.', VERDE)
marcar(L[5])
par_after(D, L[5], 'Además del avance frontal, se evaluará un modo estático en el que el dron se mantiene en vuelo '
          'estacionario y no se desplaza por sí mismo; en ese modo la única respuesta posible es el ascenso vertical '
          'cuando una persona se aproxima. No se contemplan desplazamientos horizontales autónomos.', VERDE)
reemplazar(D, L[9], 'tendrá prioridad sobre el comando manual de avance frontal.',
           'tendrá prioridad sobre el comando manual de avance frontal, pero no sobre la parada de emergencia ni sobre '
           'el cambio de modo que hace el piloto con el radiocontrol.')
r = par_after(D, L[9], '[REVISAR: los cambios a alcances y limitaciones son ajustes menores para que no se contradigan '
              'entre sí (la carta decía a la vez "dron fijo sin evasión" y "detención y ascenso"). Antes de entregar, '
              'preguntar al asesor si hay que informar al comité el cambio de Raspberry Pi a Jetson Orin Nano, porque '
              'la carta del 01/09/2026 todavía dice Raspberry Pi.]', TURQ, copiar_formato=False)

# =====================================================================
# 4. Estado del arte (recorte)
# =====================================================================
rev_after(P[209], 'recorte: se quitan las portadas de trabajos de grado (Figuras 6 a 9) y los dos antecedentes '
                'menos relacionados (fotogrametría en Madrid y control cerebro-computador). Ahorro: unas 3 páginas')
for i in (231,):
    reemplazar(D, P[i], 'El trabajo citado se identifica en la Figura 6.', '')
for i in (232, 233, 234, 235, 236, 237, 238, 240, 241, 242, 244, 245, 246, 247):
    marcar(P[i])
reemplazar(D, P[239], 'El trabajo citado se identifica en la Figura 8.', '')
reemplazar(D, P[243], 'El trabajo citado se identifica en la Figura 9.', '')
revisar(P[243], 'no se encontró ningún registro de este trabajo en línea; conseguir la ficha en la biblioteca de la USB o '
                'quitar este antecedente')
reemplazar(D, f('(Analog Devices, 2021)'), 'Analog Devices, 2021', 'Brand, 2021')
fin_arte = f('En conjunto, los antecedentes revisados muestran', 240, 260)
par_after(D, fin_arte, '[REVISAR: falta un antecedente sobre sistemas que combinan un componente aprendido con una '
          'envolvente de reglas de seguridad verificables (en la literatura aparece como "safety envelope" o "run-time '
          'assurance"). Es el respaldo directo de la arquitectura de 2.2.6. Se sugiere agregar uno y citarlo en la '
          'Tabla N3.]', TURQ, copiar_formato=False)

# =====================================================================
# 5. Marco teórico
# =====================================================================
p = f('En términos de operación, esta latencia se vuelve especialmente relevante')
marcar(p)
p_lat = par_after(D, p, 'En términos de operación, esta latencia se vuelve especialmente relevante cuando el sistema depende de '
          'una computadora externa al autopiloto para tomar decisiones. En ArduPilot, la computadora de a bordo manda '
          'consignas en el modo GUIDED por MAVLink y, si dejan de llegar durante el tiempo fijado por el parámetro '
          'GUID_TIMEOUT, la controladora detiene el vehículo por su cuenta (ArduPilot, s. f.-a).', VERDE)
h = P[286]  # 1.7 Marco conceptual
nuevo = seq(p_lat, [
    ('h3', '1.6.6 Clasificador de riesgo mediante un perceptrón multicapa'),
    ('p', 'Un perceptrón multicapa (MLP) es una red neuronal de capas totalmente conectadas que aprende una función a '
          'partir de ejemplos etiquetados mediante retropropagación del error (Rumelhart et al., 1986). En este '
          'proyecto se usa como clasificador: recibe un vector x con quince medidas de los sensores y entrega la '
          'probabilidad de que exista riesgo en los próximos segundos:'),
    ('p', 'p = σ( W₃ · ReLU( W₂ · ReLU( W₁ · x + b₁ ) + b₂ ) + b₃ )        (13)'),
    ('p', 'donde W₁, W₂ y W₃ son las matrices de pesos de las capas (32 y 16 neuronas ocultas), b₁, b₂ y b₃ los sesgos, '
          'ReLU(z) = max(0, z) la función de activación y σ la función logística. La decisión discreta se obtiene con un '
          'umbral τ y una persistencia de k cuadros:'),
    ('p', 'intervenir(t) = 1   si   p(t − j) ≥ τ  para  j = 0, …, k − 1;   0 en otro caso        (14)'),
    ('p', 'Con esta formulación, la condición R_obs de la ecuación (9) deja de ser un único umbral de distancia: el '
          'clasificador combina distancia, tamaño de la caja, velocidad de acercamiento y persistencia de la detección, '
          'y las reglas de la ecuación (10) se conservan como una envolvente que la red no puede saltar. La '
          'implementación usa scikit-learn (Pedregosa et al., 2011).'),
])

# =====================================================================
# 6. Marco conceptual (recorte)
# =====================================================================
rev_after(P[286], 'recorte: se eliminan 1.7.5 y 1.7.6, que repiten 1.6.1, y las figuras tomadas de blogs, Medium y '
                'ResearchGate (fuentes no académicas). Ahorro: unas 3 páginas')
for i in (290, 291, 292, 302, 303, 304, 305, 306, 307, 308, 309, 310, 311, 312, 313, 314, 315, 316, 317, 321, 322, 323):
    marcar(P[i])
revisar(P[297], 'mejor reemplazar esta foto de internet por una foto propia de la Pixhawk 2.4.8 montada en el dron')
reemplazar(D, P[299], 'la Raspberry Pi y la Pixhawk', 'la Jetson Orin Nano y la Pixhawk')
reemplazar(D, P[301], 'La Figura 13 resume ese flujo de procesamiento.', '')
reemplazar(D, P[320], 'La Figura 16 ilustra el tipo de maniobra considerada.', 'La Figura N2 (capítulo 2) muestra '
           'la secuencia de estados de la maniobra.')

# =====================================================================
# 7. Marco normativo (correcciones menores)
# =====================================================================
p = f('Más allá el SG-SST del marco aeronáutico')
reemplazar(D, p, 'Más allá el SG-SST del marco aeronáutico', 'Más allá del marco aeronáutico')
reemplazar(D, p, 'dentro de instalaciones universitarias', 'en un campo de pruebas al aire libre')

# =====================================================================
# 8. Metodología (solo Raspberry → Jetson y la figura)
# =====================================================================
reemplazar(D, P[361], 'la capacidad de la Raspberry Pi', 'la capacidad de la computadora de a bordo')
reemplazar(D, P[362], 'en la Raspberry Pi', 'en la computadora de a bordo (Jetson Orin Nano)')
p = f('Como instrumentos de recolección se utilizarán', 339, 367)
par_after(D, p, '[REVISAR: la metodología no se tocó. Sugerencia opcional, solo si el asesor la aprueba, para agregar '
          'al final de este párrafo: "Como instrumento complementario se usará una simulación del sistema con sensores '
          'modelados, que reproduce el protocolo de ensayo con un número alto de repeticiones y permite comparar la '
          'decisión basada en reglas con la decisión del clasificador."]', TURQ, copiar_formato=False)
marcar(P[365])
_nota_met = None
_rev_met = ('la imagen original dice "Raspberry Pi" y "entorno indoor"; se reemplaza por la misma figura con '
                'esos dos textos corregidos (debajo, en verde)')
fig = figura_after(D, P[365], f'{DIAG}/05_metodologia_corregida.png', ancho_cm=15.5)
_nota_met = par_after(D, fig, 'Figura corregida: "computadora de a bordo" y "entorno exterior" en lugar de "Raspberry Pi" y '
          '"entorno indoor"; "en la Jetson Orin Nano" en lugar de "en Raspberry Pi". El resto de la figura no cambia.',
          VERDE, style='Normal')
rev_after(_nota_met, _rev_met)

# =====================================================================
# 9. Capítulo 2.1
# =====================================================================
p = f('caja transparente para detallar la arquitectura operacional')
reemplazar(D, p, 'subsistema de gestión de potencia (UBEC) para proveer una regulación estable de 5V/3A',
           'subsistema de gestión de potencia (un convertidor DC-DC tipo buck que entrega 12 V a la Jetson)')
reemplazar(D, p, 'una cámara CSI', 'una cámara USB')
reemplazar(D, p, 'alojado en la Raspberry Pi', 'alojado en la Jetson Orin Nano')
reemplazar(D, p, 'en un script de Python estructurado bajo una lógica de umbrales críticos',
           'en un programa de Python en el que un clasificador de riesgo decide dentro de reglas de seguridad')
revisar(p, 'las Figuras 17, 18 y 19 son imágenes. La Figura 18 dice "Raspberry Pi", "Cámara CSI" y "UBEC 5V/3A" y '
           'repite el bloque "Fusión y lógica de decisión"; hay que rehacerla con la Jetson, la cámara USB y el buck '
           'de 12 V. Revisar también la 17 y la 19')
p = f('subdivide en tareas orientadas a suministrar una alimentación de 5V/3A')
reemplazar(D, p, 'una alimentación de 5V/3A aislada de interferencias', 'una alimentación regulada (12 V) aislada de '
           'interferencias')
p = f('la unidad de procesamiento (Raspberry Pi)')
insertar_tras(p, 'coherencia con la misión.', ' Esta condición inicial cambió durante la integración: la Raspberry Pi '
              'se reemplazó por una NVIDIA Jetson Orin Nano por las razones expuestas en 2.2.5. Las tablas de este '
              'apartado conservan la evaluación original, porque documentan cómo se tomó la decisión en su momento; la '
              'Tabla N1 resume lo que finalmente se implementó.')
marcar(P[393])
rev_after(P[392], 'para cumplir el límite de 100 páginas: mover las Tablas 2, 3 y 4 (generación de conceptos, juicios de '
          'fiabilidad y filtrado) a un anexo "G. Diseño conceptual detallado" y dejar aquí un párrafo de resumen por '
          'cada una. Ocupan unas 7 páginas. La versión limpia de esta copia todavía da unas 95 páginas de cuerpo sin '
          'los resultados de campo')

# Pugh: párrafo de pesos (texto dañado) y escala
marcar(P[421])
p421 = par_after(D, P[421], 'Antes de evaluar las opciones de hardware y software se estableció qué tan crítico es cada '
                 'requerimiento para el éxito del vuelo al aire libre, con una ponderación de 1 a 10 (Tabla 7). Los '
                 'valores de 1 a 3 corresponden a características de baja prioridad o prescindibles; de 4 a 7, a '
                 'funciones útiles que no condicionan la seguridad operativa; y de 8 a 10, a funciones de las que '
                 'depende la seguridad o la existencia misma del sistema. Con peso 8 quedó la gestión de potencia y '
                 'masa (RF-07): aislar el voltaje de la computadora es indispensable, pero es un respaldo físico '
                 'subordinado a la lógica de evasión. Con peso 9 quedaron la telemetría de proximidad (RF-03), el '
                 'enlace MAVLink (RF-05/RF-06) y la tolerancia al viento con failsafe (RF-08/RF-11): si el láser no mide '
                 'bien, si la orden no llega al autopiloto o si el viento desestabiliza el dron, se produce una '
                 'colisión. Con peso 10 quedaron la percepción visual e inferencia (RF-01/RF-02) y el procesamiento a '
                 'bordo (RF-04), porque sin ellos el sistema propuesto no existe.', VERDE, copiar_formato=False)
seq(p421, [
    ('p', '¿Por qué una escala de 1 a 10 y no de 1 a 5? El método de Pugh original compara cada alternativa contra una '
          'referencia con tres niveles (mejor, igual o peor), y las matrices ponderadas suelen usar escalas de 1 a 5 o '
          'de 1 a 10 (Pugh, 1991; Ulrich y Eppinger, 2016). Ninguna escala es correcta por definición; lo que la hace '
          'defendible es que cada nivel tenga un significado verificable y que la elección no cambie el resultado. '
          'Aquí se usó 1 a 10 por dos razones. Primero, la resolución: varias alternativas de una misma subfunción '
          'quedan a menos de un punto en una escala de 5 niveles y se empatarían; con 10 niveles se distinguen. '
          'Segundo, cada uno de los diez niveles quedó anclado a una descripción concreta en el texto que acompaña a '
          'las Tablas 8, 9 y 10. Para comprobar que la escala no decide el resultado, la Tabla N2 repite la '
          'comparación pasando cada calificación a la escala de 1 a 5 (redondeando hacia arriba la mitad del valor): '
          'dentro de cada subfunción el orden de las alternativas no cambia.'),
])
p = f('Teniendo en cuenta la ponderación obtenida en la Tabla 9')
reemplazar(D, p, 'Tabla 9', 'Tabla 8')
p = f('Teniendo en cuenta la ponderación de la Tabla 10')
reemplazar(D, p, 'Tabla 10', 'Tabla 9')
revisar(f('Radar mmWave: Presenta alta masa'), 'en la integración la cámara CSI falló en la Jetson y se terminó usando '
        'una cámara web USB (2.2.5); con TensorRT la latencia de la USB no resultó limitante (30 cuadros/s de cámara y '
        '9–11 ms de inferencia). Conviene decirlo aquí en una frase')

# Tabla N2: sensibilidad de la escala (cálculo en este script)
import math
pesos8 = [10, 9, 9, 8, 9]
pesos9 = [10, 10, 8, 8, 9]
T8 = {'Cámara CSI': [9, 0, 9, 9, 8], 'Cámara web USB': [7, 0, 5, 7, 6], 'Cámara de acción': [4, 0, 2, 3, 5],
      'LiDAR ToF': [0, 9, 9, 9, 8], 'Ultrasónico': [0, 2, 4, 8, 1], 'Radar mmWave': [0, 8, 7, 4, 9]}
T9 = {'Raspberry Pi 4': [8, 8, 8, 8, 10], 'Jetson Nano': [10, 9, 6, 4, 9], 'Teensy 4.1': [1, 2, 8, 9, 3],
      'YOLO Nano': [9, 9, 0, 9, 9], 'EfficientDet/MobileNet': [7, 6, 0, 7, 7], 'UBEC dedicado': [0, 0, 10, 9, 0],
      'Batería secundaria': [0, 0, 7, 3, 0]}
grupos = [('Cámara', T8, pesos8, ['Cámara CSI', 'Cámara web USB', 'Cámara de acción']),
          ('Distancia', T8, pesos8, ['LiDAR ToF', 'Radar mmWave', 'Ultrasónico']),
          ('Procesador', T9, pesos9, ['Raspberry Pi 4', 'Jetson Nano', 'Teensy 4.1']),
          ('Modelo', T9, pesos9, ['YOLO Nano', 'EfficientDet/MobileNet']),
          ('Potencia', T9, pesos9, ['UBEC dedicado', 'Batería secundaria'])]


def tot(v, w, esc5=False):
    return sum((math.ceil(x / 2) if esc5 else x) * wi for x, wi in zip(v, w))


filas = [['Subfunción', 'Alternativa', 'Total escala 1–10', 'Puesto', 'Total escala 1–5', 'Puesto']]
for g, T, w, alts in grupos:
    s10 = sorted(alts, key=lambda a: -tot(T[a], w))
    s5 = sorted(alts, key=lambda a: -tot(T[a], w, True))
    for a in alts:
        filas.append([g, a, tot(T[a], w), s10.index(a) + 1, tot(T[a], w, True), s5.index(a) + 1])
p = f('Una vez ponderados los requerimientos, la Tabla 8')
ult = seq(P[438], [
    ('tabla', 'Tabla N2', 'Sensibilidad de la matriz de decisión a la escala de calificación', filas,
     [2.4, 4.2, 2.4, 1.4, 2.4, 1.4],
     'Nota. Se usaron las calificaciones de las Tablas 8 y 9 y los pesos de la Tabla 7 asignados a cada criterio '
     '(Tabla 8: 10, 9, 9, 8, 9; Tabla 9: 10, 10, 8, 8, 9). Escala 1–5 = mitad de la calificación, redondeada hacia '
     'arriba.'),
    ('rev', 'los "puntajes totales ponderados" de las Tablas 8 y 9 no se pueden reproducir con los pesos de la Tabla 7: '
            'se probaron todas las combinaciones de pesos enteros de 1 a 10 y ninguna da esos totales. Por eso la Tabla '
            'N2 recalcula con una asignación explícita de pesos. Hay que agregar a las Tablas 8 y 9 una columna "Peso" '
            'con el valor usado en cada fila y rehacer la suma; un jurado lo puede comprobar con una calculadora'),
    ('p', 'Reevaluación con los datos de la integración. La Tabla 9 calificó la Raspberry Pi 4 con 8 en inferencia, '
          'latencia y estabilidad de potencia, y descartó la Jetson Nano por consumo y masa. En las pruebas de 2.2.5 la '
          'Raspberry Pi mostró caídas de tensión, fallos de arranque que corrompieron el sistema operativo y un cuello '
          'de botella en la inferencia; la Jetson Orin Nano (una generación posterior a la Jetson Nano evaluada) '
          'procesa cada cuadro en 9 a 11 ms con TensorRT y no presentó reinicios con el convertidor de 12 V. Con esas '
          'calificaciones medidas (Raspberry Pi 4: 4, 4, 3, 8, 10; Jetson Orin Nano: 10, 10, 8, 5, 9) los totales '
          f'quedan en {tot([4, 4, 3, 8, 10], pesos9)} y {tot([10, 10, 8, 5, 9], pesos9)} puntos, y la selección se '
          'invierte. La matriz cumplió su función con la información disponible; lo que falló fue la calificación '
          'supuesta de la Raspberry Pi, que solo se pudo corregir midiendo.'),
    ('rev', 'las calificaciones "medidas" de este párrafo son una propuesta (4, 4, 3 para la Raspberry Pi; 10, 10, 8, '
            '5, 9 para la Jetson Orin Nano). Ajustarlas con lo que de verdad se observó'),
])
p = f('Finalmente, la Tabla 10')
reemplazar(D, p, 'La Figura 21 representa gráficamente el concepto global seleccionado.',
           'La Figura 20 representa gráficamente el concepto global seleccionado.')
rev_after(T_ORIG[11]._tbl, 'la Tabla 10 está mal: repite las filas y los puntajes de la Tabla 9 (inferencia, latencia, '
                'integración con Python…) en lugar de calificar el control de vuelo. Hay que rehacerla con criterios '
                'propios de la función 3, por ejemplo: código abierto e integración, rutinas de failsafe, control externo '
                'seguro (GUIDED), comunicación bidireccional y disponibilidad. La escala del párrafo anterior ya los '
                'describe')
# Concepto global: diseñado vs implementado
tabla11 = T_ORIG[12]._tbl
filasN1 = [
    ['Subsistema', 'Concepto del diseño (Tabla 11)', 'Implementado', 'Motivo del cambio'],
    ['Computación de a bordo', 'Raspberry Pi 4 Model B', 'NVIDIA Jetson Orin Nano (Ubuntu 24.04, JetPack 7)',
     'Caídas de tensión, fallos de arranque y cuello de botella en la inferencia (2.2.5)'],
    ['Cámara', 'Cámara nativa CSI', 'Cámara web USB, 640×480, 30 cuadros/s, HFOV medido 38.9°',
     'La cámara CSI IMX219 daba pantallas verdes y bloqueaba nvargus-daemon'],
    ['LiDAR', 'TF-Luna', 'Benewake TF03 (UART por convertidor USB-TTL), 100 Hz',
     'Alcance de 0.1 a 70 m sobre superficies oscuras (10 % de reflectividad; Benewake, s. f.), frente a unos 8 m del '
     'TF-Luna; en exteriores hace falta ver el panel a más de 20 m. [REVISAR: confirmar que la unidad es la TF03-180]'],
    ['Detector', 'YOLO versión Nano', 'YOLO26n preentrenado (COCO) en TensorRT FP16, 9–11 ms por cuadro',
     'Aceleración por GPU de la Jetson'],
    ['Decisión', 'Lógica de umbrales críticos', 'Clasificador MLP 32-16 dentro de una envolvente de reglas',
     'Menos activaciones innecesarias con la misma seguridad (capítulo 3)'],
    ['Potencia lógica', 'UBEC 5 V / 3 A', 'Convertidor DC-DC buck a 12.02 V para la Jetson',
     'La Jetson consume más que la controladora y necesita su propia línea (RF-07)'],
    ['Enlace', 'MAVLink por UART', 'MAVLink 2 por TELEM2 a 115200 baudios, sin 5 V',
     'A 460800 y 921600 baudios la Pixhawk no entendía a la Jetson'],
    ['Estabilizador de cámara', '—', 'BaseCam SimpleBGC de 2 ejes; pitch fijo en −5° por PWM desde AUX1',
     'El firmware 2.2 no obedece comandos por serie; el pitch se manda con DO_SET_SERVO'],
    ['Posicionamiento', '—', 'GPS de la Pixhawk', 'El modo GUIDED exige fijación GPS 3D en exteriores'],
]
cap = par_after(D, tabla11, 'Tabla N1', AMARILLO, bold=True, style='Normal')
cap2 = par_after(D, cap, 'Concepto global diseñado frente al implementado', AMARILLO, italic=True, style='Normal')
tN1 = tabla_after(D, cap2._p, filasN1, [3.0, 3.4, 4.6, 5.0])
nota_after(D, tN1, 'Nota. Datos de docs/hardware.md y docs/pixhawk.md del repositorio.')
rev_after(P[443], 'esta figura muestra el concepto del diseño (Raspberry Pi, '
        'cámara CSI, TF-Luna, UBEC). Se puede dejar como registro histórico si el texto aclara que el implementado es '
        'el de la Tabla N1')
for txt in ('Nota. Elaboración por Gemini.',):
    for p in P[440:455]:
        if p.text.strip().startswith('Nota. Elaboración por Gemini'):
            reemplazar(D, p, 'Elaboración por Gemini.', 'Elaboración propia con apoyo de una herramienta de IA '
                       'generativa (Gemini).')
            revisar(p, 'confirmar cómo pide la universidad declarar el uso de IA generativa; lo más seguro es '
                       'reemplazar esta imagen por una foto real del dron')

# 2.1.10 LiDAR
reemplazar(D, P[470], 'TF-Luna', 'TF03')
reemplazar(D, P[471], 'se interconecta de manera directa a la Raspberry Pi, compartiendo el entorno de procesamiento '
           'simultáneo con el flujo de video capturado por la cámara CSI',
           'se conecta a la Jetson Orin Nano mediante un convertidor USB–TTL y entrega 100 lecturas por segundo, en '
           'paralelo con el flujo de video de la cámara USB')
marcar(P[473])
par_after(D, P[473], 'En el sistema implementado la lógica es distinta, porque el LiDAR es un único rayo fijo y no '
          'siempre incide sobre la persona. El LiDAR decide el riesgo frente a obstáculos (paneles) con la distancia de '
          'seguridad d_safe, y el riesgo frente a personas se evalúa con la distancia estimada por el tamaño de la caja '
          'de YOLO, su velocidad de acercamiento y el clasificador de 2.2.6. La lectura del LiDAR es además una de las '
          'entradas de ese clasificador, y cualquier lectura menor de 3 m mientras el dron avanza detiene el avance sin '
          'importar lo que decida la IA (bloqueo frontal).', VERDE, copiar_formato=False)


def dsafe(v):
    return v * 0.5 + v * v / (2 * 2.5) + 1.5 + 0.4


filas_ds = [['Velocidad de avance (m/s)', 'Reacción v·T (m)', 'Frenado v²/2a (m)', 'Margen + radio (m)',
             'd_safe (m)', 'Distancia mínima al panel en simulación (m)']]
holg = {1: '1.77 [1.73, 1.82]', 2: '3.14 [3.09, 3.18]', 3: '4.34 [4.29, 4.39]', 4: '5.35 [5.30, 5.40]'}
for v in (1, 2, 3, 4):
    filas_ds.append([v, f'{v * 0.5:.1f}', f'{v * v / 5:.1f}', '1.9', f'{dsafe(v):.1f}', holg[v]])
seq(P[479], [
    ('p', 'Valores usados en el sistema implementado y su origen:'),
    ('li', 'T_loop = 0.5 s. Incluye la latencia medida en simulación entre el riesgo y el comando (alrededor de 0.1 s, '
           'con un retardo de sensores de 100 ms) y el tiempo que tarda el controlador de ArduPilot en empezar a frenar. '
           'Es un valor conservador frente a los 9–11 ms de inferencia medidos en la Jetson.'),
    ('li', 'a_max = 2.5 m/s². Es la aceleración de frenado por defecto de ArduPilot en el modo LOITER (parámetro '
           'LOIT_BRK_ACCEL = 250 cm/s²; ArduPilot, s. f.-c), el modo en el que vuela el piloto durante la prueba. '
           '[REVISAR: confirmar el valor leyéndolo en la propia Pixhawk con Mission Planner; el 250 cm/s² sale de '
           'foros de ArduPilot, no de la página oficial de parámetros]'),
    ('li', 'd_margen = 1.5 m más 0.4 m de radio del dron (medio brazo del chasis ZD550 más el radio de la hélice). '
           '[REVISAR: justificar el 1.5 m con una fuente o con el error del LiDAR más el error de posición; hoy es una '
           'elección de diseño]'),
    ('p', 'Además de d_safe, el sistema considera riesgo cuando faltan menos de 2.5 s para tocar el obstáculo y, '
          'siempre, cuando el LiDAR mide menos de 3 m mientras el dron avanza. La Tabla N3 da d_safe para las '
          'velocidades del protocolo y la compara con la holgura mínima al panel obtenida en 100 vuelos simulados por '
          'velocidad (entre corchetes, el intervalo de confianza del 95 %).'),
    ('tabla', 'Tabla N3', 'Distancia de seguridad por velocidad de avance', filas_ds, [2.6, 2.2, 2.4, 2.2, 1.8, 4.2],
     'Nota. d_safe = v·0.5 + v²/(2·2.5) + 1.5 + 0.4. Holgura en simulación: simulacion/informes/'
     'minimo_tesis_protocolo.md (escenario a).'),
])

# =====================================================================
# 10. Capítulo 2.2
# =====================================================================
p = f('a 921600 baudios y con MAVLink 2')
reemplazar(D, p, 'a 921600 baudios y con MAVLink 2',
           'a 115200 baudios y con MAVLink 2 (a 460800 y 921600 baudios la Pixhawk no interpretaba lo que transmitía '
           'la Jetson, por la imprecisión del reloj del UART de la Jetson al transmitir)')
reemplazar(D, p, 'y la cámara, por USB o por el conector CSI', 'y la cámara, por USB')
insertar_tras(p, '/dev/serial/by-id/.', ' El pitch del estabilizador se ordena por PWM desde la salida AUX1 de la '
              'Pixhawk con el comando DO_SET_SERVO, con la relación pwm = 1500 + θ·500/45 µs (±45° entre 1000 y '
              '2000 µs), porque el firmware 2.2 de la BaseCam no obedece los comandos por puerto serie. En el mínimo '
              'indispensable se deja fijo en −5°.')
for p in P[491:500]:
    if 'Elaboración Gemini' in p.text:
        reemplazar(D, p, 'Elaboración Gemini.', 'Elaboración propia con apoyo de una herramienta de IA generativa '
                   '(Gemini).')
        revisar(p, 'a la figura le faltan la salida AUX1 hacia la BaseCam (PWM del pitch), el GPS y la cámara USB')
p = f('asignación de los modos de vuelo al interruptor')
reemplazar(D, p, 'La Tabla 16 resume', 'La Tabla 13 resume')
revisar(p, 'los modos no coinciden entre documentos: docs/pixhawk.md registra STABILIZE / ALT_HOLD / GUIDED en CH5, y '
           'el plan del mínimo propone ALT_HOLD / LOITER / LAND en CH5 con CH7 como interruptor del modo experimental. '
           'Dejar aquí la configuración final que confirme la sesión física')
insertar_tras(P[516], 'para desplegar la información correspondiente.', ' Esta descripción corresponde a la primera '
              'versión del detector, que solo monitoreaba. En la versión final, la decisión de intervenir y el envío de '
              'comandos están en el módulo de decisión descrito en 2.2.6.')
reemplazar(D, P[531], 'Ubuntu 20.04.6 LTS, Python 3', 'Ubuntu 24.04 (L4T R39.2.1, JetPack 7), Python 3.12')
p = P[531]
reemplazar(D, p, 'La opción tiene una razón concreta: el OpenCV que se instala con pip se compila sin soporte de '
           'GStreamer, y la cámara CSI de la Jetson solo se abre mediante un pipeline de GStreamer (nvarguscamerasrc). '
           'Al heredar los paquetes del sistema, el entorno usa el OpenCV de JetPack, que sí lo incluye, y el programa '
           'abre la cámara con una función que construye el pipeline a mano.',
           'La opción permite usar las bibliotecas que trae JetPack (TensorRT y CUDA) dentro del entorno virtual.')
reemplazar(D, P[532], 'se pasó a una cámara Basecam Gimabl; el código conserva ambas fuentes',
           'se pasó a una cámara web USB (Sonix, 640×480, campo de visión horizontal medido de 38.9°) montada sobre el '
           'estabilizador BaseCam')
reemplazar(D, P[532], 'El modelo puede exportarse además a TensorRT (yolo export ... format=engine half=True) para '
           'elevar la tasa de cuadros.',
           'El modelo YOLO26n se exportó a TensorRT en media precisión (FP16): cada cuadro tarda entre 9 y 11 ms en la '
           'Orin, frente a los 33 ms que separan dos cuadros de la cámara a 30 cuadros por segundo.')
rev_after(P[536], 'hay dos "Figura 28" (esta y el diagrama de evasión de 2.2.6); renumerar')

# 2.2.6 lógica
marcar(P[539]); marcar(P[540]); marcar(P[541])
revisar(P[538], 'el diagrama "Algoritmo de evasión" (Figura 28) muestra evasión a izquierda y derecha y un umbral '
                'de 60 %, que contradicen la limitación de evasión solo vertical. Se reemplaza por las Figuras N2 y N3')
seq(P[541], [
    ('fig', 'Figura N2', 'Arquitectura híbrida de percepción, decisión y control',
     f'{DIAG}/01_arquitectura.png', None),
])
marcar(P[542])
par_after(D, P[542], 'La cámara alimenta a la IA 1, el detector YOLO26n con seguimiento descrito en 2.2.4. En el mínimo '
          'indispensable el estabilizador no sigue a la persona: mantiene la cámara y el LiDAR con una inclinación fija '
          'de −5°, de modo que el LiDAR mide lo que hay al frente, en la trayectoria. De cada cuadro se calculan quince '
          'entradas para la IA 2: de la caja de YOLO, el alto, el ancho, el área, el ángulo horizontal y su variación, '
          'la confianza y el número de cuadros seguidos con detección; del LiDAR, la distancia y si la lectura es '
          'utilizable; de la Pixhawk, la velocidad propia que estima su filtro EKF; y de un seguimiento alfa-beta de la '
          'persona, la distancia, la velocidad de acercamiento, la velocidad lateral y el tiempo sin detección. Las '
          'entradas se calculan con la misma función en la simulación y en el dron, para que el modelo reciba en vuelo '
          'lo mismo que vio al entrenarse.', VERDE, copiar_formato=False)
marcar(P[543])
p543 = par_after(D, P[543], 'La IA 2 es un perceptrón multicapa de scikit-learn con dos capas ocultas de 32 y 16 '
                 'neuronas (ReLU) y una sola salida: la probabilidad de que, si el piloto mantiene su mando, en los '
                 'próximos 3 s ocurra un choque o una persona quede a menos de 2 m del dron. Si esa probabilidad supera '
                 '0.7 durante 2 cuadros seguidos, el sistema pasa de CONTINUAR a DETENER_Y_ASCENDER. No hay salidas de '
                 'evasión lateral, lo que respeta la limitación de 1.4.2. El modelo se entrenó con 2 551 725 cuadros de '
                 'vuelos simulados sin intervención (13 % con riesgo), etiquetados automáticamente con la verdad del '
                 'simulador, sin etiquetado manual; se validó con 499 021 cuadros y se probó con 533 085 cuadros de '
                 'mundos que no participaron en el entrenamiento. En la prueba obtuvo un área bajo la curva ROC de '
                 '0.974, una precisión de 97.0 %, una exhaustividad por cuadro de 74.4 % y una tasa de falsos positivos '
                 'de 0.3 %. La exhaustividad por cuadro no mide la seguridad: un riesgo dura muchos cuadros y basta con '
                 'detectarlo en dos seguidos; la seguridad se mide en lazo cerrado (capítulo 3). El umbral y el número '
                 'de cuadros se eligieron en lazo cerrado con los mundos de validación, nunca con el protocolo. El '
                 'modelo se exporta como decision.pkl y como un archivo JSON con los pesos, que la Jetson evalúa con '
                 'NumPy (unas 1 000 multiplicaciones por cuadro).', VERDE, copiar_formato=False)
revisar(p543, 'falta validar el clasificador con datos reales del dron (pasos 4 y 5 del plan físico). Si con datos '
              'reales rinde distinto, se reporta tal cual')
marcar(P[544])
p544 = par_after(D, P[544], 'La salida del clasificador opera dentro de una envolvente de reglas que no puede saltar: '
                 '(1) si el LiDAR mide menos de 3 m mientras el dron avanza, se detiene el avance sin importar lo que '
                 'diga la IA (bloqueo frontal); (2) el ascenso por una persona solo lo autoriza el árbitro de seguridad, '
                 'cuando la persona está a menos de 3 m, o a menos de 8 m y acercándose; antes de eso la IA solo puede '
                 'detener; (3) una salvaguarda geométrica detiene el dron si una persona seguida va a pasar a menos de '
                 '2 m en menos de 1.5 s; y (4) la parada de emergencia del radiocontrol (CH8) y el cambio de modo del '
                 'piloto mandan siempre. El programa nunca arma ni despega por sí mismo y, si falta la cámara, el '
                 'detector o el LiDAR, detiene el avance (RF-11). La Figura N3 muestra los estados de la maniobra.',
                 VERDE, copiar_formato=False)
seq(p544, [
    ('fig', 'Figura N3', 'Estados de la intervención', f'{DIAG}/02_estados.png',
     'Nota. CH7: interruptor del modo experimental; CH5: modo de vuelo; CH8: parada de emergencia. '
     '[REVISAR: confirmar los canales con la sesión física]'),
])
reemplazar(D, P[545], 'La secuencia de vuelo prevista es despegar en STABILIZE, pasar a LOITER para confirmar el GPS, '
           'superar los 2 m de altura y entonces pasar a GUIDED.',
           'En la secuencia prevista para el mínimo indispensable, el piloto despega y vuela en LOITER a 2.3 m, activa '
           'el modo experimental con un interruptor del radiocontrol y avanza; solo cuando el sistema decide '
           'intervenir, la Jetson cambia la Pixhawk a GUIDED, anula la velocidad horizontal y ordena subir hasta '
           '3.30 m con una consigna de posición. El piloto retoma el mando moviendo el interruptor de modos.')
revisar(P[545], 'las Tablas 21 y 22 y el Anexo C no existen todavía; ver la propuesta de anexos al final')
reemplazar(D, P[547], 'la Tabla 17', 'la Tabla 14')

# Tabla 14: estados actualizados
t14 = T_ORIG[15]
nuevos = {3: 'Verificada: TF03 a 100 Hz por USB-TTL (6 de octubre de 2026)',
          4: 'Verificada la lectura de ángulos por USB; el control por UART se descartó (firmware 2.2) y el pitch va por '
             'PWM desde AUX1',
          5: 'Verificada: TELEM2 a 115200 baudios, DO_SET_SERVO 10 de 10 con confirmación (ACK)'}
from helpers import new_run
from docx.oxml.ns import qn
for fila, texto in nuevos.items():
    cel = t14.cell(fila, 3)
    par = cel.paragraphs[0]
    for r in par._p.iter(qn('w:r')):
        from helpers import hl
        hl(r, par, ROJO)
    new_run(par, ' ' + texto, VERDE)
revisar(P[553], 'falta insertar las capturas de la Figura 29 (la figura está vacía)')

marcar(P[556])
p556 = par_after(D, P[556], 'La verificación de 2.2.7 y las pruebas de banco posteriores cubren la percepción y la '
                 'comunicación: la aeronave integrada detecta personas con su propia alimentación, el LiDAR TF03 '
                 'entrega 100 lecturas por segundo y el enlace MAVLink con la Pixhawk responde (10 de 10 comandos con '
                 'confirmación). Antes de volar quedan cinco comprobaciones: que la BaseCam, alimentada, lea el pulso '
                 'de AUX1; el cambio a GUIDED y la retoma del piloto en banco, midiendo la latencia entre el riesgo y '
                 'el comando (criterio: menos de 150 ms); la grabación de datos reales con el dron sin hélices sobre un '
                 'carrito, para comparar los sensores con su modelo de simulación; el decisor en modo sombra, que '
                 'decide y registra pero no manda; y la fijación GPS 3D que exige GUIDED.', VERDE,
                 copiar_formato=False)
revisar(p556, 'actualizar con lo que reporte la sesión "Desarrollo Dron Parte Física" (pasos 0 a 7 de '
              'docs/PLAN_MINIMO_FISICO.md)')
reemplazar(D, P[557], 'cuyo protocolo se desarrolla en el capítulo 3 con las listas del Anexo B',
           'cuyo protocolo se describe en 2.3 y cuyas listas de verificación van en el Anexo F')

# =====================================================================
# 11. Nuevo 2.3: protocolo de validación y porqué de cada número
# =====================================================================
filas_umbral = [
    ['Valor', 'Dónde se usa', 'Por qué ese valor'],
    ['2.3 m', 'Altura de vuelo del piloto durante la prueba',
     'Con la cámara y el LiDAR a −5°, el rayo toca el suelo a unos 26 m (2.3 / tan 5°): ese es el alcance útil del '
     'LiDAR. El panel de 2.6 m queda por encima del rayo, así que el LiDAR lo ve. [REVISAR: confirmar el origen del '
     '2.3 m en las decisiones de diseño]'],
    ['3.30 m', 'Altura segura a la que sube el dron al intervenir',
     'En el modelo, una persona alcanza al dron si este está a menos de 1.0 m en horizontal y por debajo de 2.6 m. '
     'Los 2.6 m representan el alcance de una persona alta con el brazo extendido y un salto. Sobre ellos se dejan '
     '0.7 m, que cubren el radio del dron (0.4 m) y el error de altura en vuelo. En simulación el dron sale de ese '
     'alcance 0.40 s después de la orden. [REVISAR: citar una fuente antropométrica para el alcance de pie y para el '
     'salto vertical de adultos no entrenados]'],
    ['1.72 m', 'Estatura que supone la Jetson para estimar la distancia por la caja',
     'Media del modelo de población (desviación 0.07 m, rango 1.58–1.88 m). Supera el promedio de los hombres '
     'colombianos nacidos entre 1980 y 1984, 170.6 cm (Meisel y Vega, 2007), así que es conservadora para el alcance. '
     'Para la distancia ocurre lo contrario: una persona más baja parece más lejos.'],
    ['2 m', 'Zona de riesgo de una persona (etiqueta del clasificador y criterio de éxito)',
     'Alcance horizontal de un brazo extendido (1.0 m) más el radio del dron (0.4 m) y un margen de 0.6 m.'],
    ['3 m', 'Bloqueo frontal del LiDAR y persona "en amenaza"',
     'Es la distancia de seguridad d_safe para unos 1.4 m/s (Tabla N3): por debajo de 3 m el dron ya no alcanza a '
     'frenar con margen a velocidades de maniobra, así que la orden es fija y no depende de la IA. Deja 1 m sobre la '
     'zona de riesgo de 2 m.'],
    ['8 m', 'Distancia a la que el árbitro autoriza subir si la persona se acerca',
     'Una persona que corre (3.3 m/s) tarda (8 − 2) / 3.3 = 1.8 s en llegar a 2 m; el sistema necesita unos 0.5 s '
     '(0.1 s de decisión y 0.4 s para salir del alcance). Con el dron avanzando a 4 m/s el acercamiento es de 7.3 m/s y '
     'el tiempo baja a 0.82 s, todavía mayor que 0.5 s; por encima de 4 m/s el margen se pierde.'],
    ['4 m/s', 'Velocidad máxima del piloto (LOIT_SPEED)',
     'Es la velocidad máxima a la que el sistema se detiene con margen ante una persona quieta usando solo reglas '
     '(barrido de 1 a 12 m/s, criterio ≥ 95 % de los vuelos).'],
    ['3 s', 'Horizonte de predicción del clasificador',
     'Cubre la reacción (0.5 s) y el frenado desde 4 m/s (0.8 s y 3.2 m) con margen.'],
    ['0.7 y 2 cuadros', 'Umbral y persistencia del clasificador',
     'Se eligieron en lazo cerrado con mundos de validación: el mínimo de activaciones innecesarias sin dejar pasar '
     'más riesgos que las reglas.'],
    ['100 ms', 'Retardo de los sensores en simulación',
     'Conservador frente a la inferencia medida (9–11 ms) y al tiempo entre cuadros (33 ms). Se probó hasta 500 ms '
     '(condiciones degradadas).'],
    ['150 ms', 'Criterio de aceptación de la latencia riesgo → comando en el dron real', 'Deja margen sobre el '
     '0.1 s de la simulación; con 300 ms la simulación sigue sin choques a las velocidades del protocolo.'],
    ['10 repeticiones', 'Repeticiones de campo por escenario',
     'Con 10 de 10 éxitos, el intervalo de Wilson del 95 % va de 72 % a 100 %: demuestra que funciona y valida '
     'latencia y frenado. Para afirmar un éxito de al menos 90 % con 95 % de confianza harían falta 35 de 35.'],
]
filas_metr = [
    ['Métrica', 'Reglas', 'IA + envolvente', 'Experimento (n)', 'Prueba estadística'],
    ['Éxito en el protocolo del comité (13 variantes)', '100 % [99.7, 100]', '100 % [99.7, 100]',
     'Protocolo, 1300 vuelos por decisor', 'Ninguna: los dos decisores cumplen todo'],
    ['Éxito en discriminación (5 escenarios)', '91.2 % [88.4, 93.4]', '94.0 % [91.6, 95.8]',
     'Discriminación, 500 vuelos por decisor', 'McNemar exacto (pares): 16 contra 2, p = 0.0013'],
    ['Activaciones innecesarias', '44', '30', 'Protocolo + discriminación, 1800 vuelos',
     'McNemar exacto (pares): 16 contra 2, p = 0.0013'],
    ['Choques', '39', '28', 'Mundos de prueba, 3840 vuelos',
     'Dos proporciones sin emparejar: p ≈ 0.18 (no significativa)'],
    ['Vuelos con una persona a < 2 m bajo 3.30 m', '420', '218', 'Mundos de prueba, 3840 vuelos',
     'Dos proporciones sin emparejar: p < 0.001'],
    ['Riesgos no evitados', '92 (2.4 %)', '67 (1.7 %)', 'Mundos de prueba, 3840 vuelos',
     'Dos proporciones sin emparejar: p ≈ 0.045'],
]
seq(P[557], [
    ('h2', '2.3 Diseño del protocolo de validación experimental'),
    ('p', 'Este apartado corresponde al tercer bloque técnico anunciado al inicio del capítulo. Define los escenarios, '
          'los criterios de éxito, el origen de cada valor numérico del sistema y la forma de analizar los datos. El '
          'mismo protocolo se ejecuta primero en simulación y después en campo, con las mismas métricas.'),
    ('h3', '2.3.1 Escenarios y criterios de éxito'),
    ('p', 'El piloto avanza en línea recta en LOITER a 2.3 m, o deja el dron en vuelo estacionario (modo estático). Los '
          'escenarios son: (a) avance hacia un panel fijo de 2 × 2.6 m a 1, 2, 3 y 4 m/s; (b) avance hacia una persona '
          'quieta a 1.5 y 3 m/s; (c) persona que viene de frente caminando (1.4 m/s) o corriendo (3.3 m/s), con avance a '
          '1 m/s; (d) persona que cruza lejos, caminando o corriendo, que no debe activar el sistema; y (e) modo '
          'estático con una persona que viene caminando o corriendo, y con una que pasa de lado a 5 m, que tampoco debe '
          'activarlo. Un vuelo es exitoso si, cuando el escenario pide activarse, el sistema se activa y no hay choque; '
          'y si, cuando no lo pide, no se activa y no hay choque. Se registran además las activaciones verdaderas y '
          'falsas, los eventos de riesgo, la latencia entre el riesgo y el comando, el tiempo hasta el frenado '
          'efectivo y las paradas del operador.'),
    ('p', 'Para comparar la decisión por reglas con la decisión de la IA se agregan cinco escenarios de discriminación, '
          'con personas que pasan cerca de la trayectoria: unas van a quedar a menos de 2 m del dron (el sistema debe '
          'activarse) y otras no (no debe activarse). El éxito se juzga por vuelo, contra lo que habría pasado en ese '
          'mismo vuelo sin el sistema.'),
    ('fig', 'Figura N4', 'Secuencia de validación, de la simulación al campo', f'{DIAG}/03_experimento.png',
     None),
    ('h3', '2.3.2 Origen de los valores numéricos del sistema'),
    ('p', 'Cada número del sistema tiene una razón física o se eligió con datos que no se usan para evaluarlo. La Tabla '
          'N4 los reúne.'),
    ('tabla', 'Tabla N4', 'Valores del sistema y su justificación', filas_umbral, [2.2, 4.2, 9.6], None),
    ('h3', '2.3.3 ¿Por qué decidir con IA y no solo con condicionales?'),
    ('p', 'Detectar a una persona en una imagen no se puede resolver con condicionales, y por eso se usa YOLO. La '
          'pregunta de fondo es otra: una vez detectada, ¿hace falta una IA para decidir si intervenir? Las medidas '
          'reales son ruidosas. La distancia estimada con el tamaño de la caja tiene errores de hasta el doble a corta '
          'distancia (medido el 7 de octubre de 2026), YOLO pierde cuadros y una persona que cruza delante puede '
          'parecerse durante un instante a una que viene de frente. Con umbrales fijos hay que escoger entre ser '
          'conservador, con detenciones innecesarias, o permisivo, con riesgos omitidos. El clasificador aprende la '
          'frontera de decisión combinando las quince medidas a la vez.'),
    ('p', 'Las reglas no desaparecen. Quedan como una envolvente que garantiza un comportamiento verificable: el '
          'bloqueo frontal por LiDAR, el árbitro que autoriza el ascenso y la parada del operador mandan sobre la IA. '
          'Así la IA aporta criterio donde las reglas fijas son ineficientes, y las reglas responden donde la IA podría '
          'fallar. La Figura N5 resume la comparación; los resultados completos están en el capítulo 3.'),
    ('fig', 'Figura N5', 'Reglas solas frente a IA con envolvente en los escenarios de discriminación',
     f'{DIAG}/04_porque_ia.png', 'Nota. Datos de simulacion/informes/minimo_tesis_decisor_ia.md.'),
    ('h3', '2.3.4 Tamaño de muestra y análisis estadístico'),
    ('p', 'Las tasas de éxito se reportan con el intervalo de confianza del 95 % de Wilson, que se comporta bien con '
          'muestras pequeñas y con proporciones cercanas a 0 o a 100 % (Wilson, 1927). En simulación se corren 100 '
          'vuelos por variante. En campo, diez repeticiones por escenario: diez éxitos de diez dan un intervalo de 72 % '
          'a 100 %, suficiente para mostrar que el sistema funciona y para medir la latencia y la distancia de frenado, '
          'pero no para afirmar una tasa fina; esa la aporta la simulación.'),
    ('p', 'Para comparar dos decisores sobre los mismos vuelos se usa la prueba de McNemar, que solo cuenta los vuelos '
          'en los que los decisores difieren (McNemar, 1947). Es la prueba adecuada porque en la simulación cada '
          'decisor enfrenta exactamente los mismos mundos (mismas semillas). Una prueba de dos proporciones que trate '
          'las muestras como independientes desperdicia ese emparejamiento: con los mismos datos de discriminación, da '
          'p = 0.09, mientras que McNemar da p = 0.0013.'),
    ('tabla', 'Tabla N5', 'Métricas principales y su fuente', filas_metr, [4.4, 2.4, 2.6, 3.2, 3.4],
     'Nota. Entre corchetes, el intervalo de Wilson del 95 %. Fuente: simulacion/informes/minimo_tesis_decisor_ia.md '
     'y minimo_tesis_decisor_ia.csv. Las pruebas de los 3840 vuelos no están emparejadas porque el archivo por vuelo de '
     'ese experimento no está en el repositorio.'),
    ('rev', 'no mezclar experimentos al citar cifras: el 94.0 % frente a 91.2 % sale de los escenarios de '
            'discriminación (500 vuelos por decisor), y los 28 frente a 39 choques y 218 frente a 420 aproximaciones '
            'salen de los 3840 mundos de prueba. Son experimentos distintos. Además, la reducción de choques no es '
            'estadísticamente significativa; no escribir "la IA reduce los choques" sin esa aclaración'),
])

# =====================================================================
# 12. Capítulo 3: resultados (esqueleto con lo verificado)
# =====================================================================
filas_lat = [
    ['Escenario', 'Riesgo → comando (s)', 'Comando → frenado efectivo (s)', 'Distancia mínima (m)'],
    ['a) Panel, 1 m/s', '0.09 [0.08, 0.10]', '0.59 [0.58, 0.60]', '1.77 [1.73, 1.82]'],
    ['a) Panel, 4 m/s', '0.10 [0.09, 0.11]', '1.39 [1.38, 1.39]', '5.35 [5.30, 5.40]'],
    ['b) Persona quieta, 3 m/s', '0.10 [0.07, 0.12]', '1.12 [1.11, 1.13]', '6.44 [6.38, 6.51]'],
    ['c) Persona que corre de frente', '0.11 [0.10, 0.13]', '0.58 [0.57, 0.59]', '5.65 [5.57, 5.72]'],
    ['e) Estático, persona que corre', '0.12 [0.09, 0.14]', '— (quieto)', '6.12 [6.05, 6.20]'],
]
filas_disc = [
    ['Escenario de discriminación', '¿Debe activarse?', 'Reglas', 'IA sola', 'IA + envolvente'],
    ['Cruza 3–4 m por delante y sigue', 'no', '95 %', '98 %', '98 %'],
    ['Cruza justo por donde pasa el dron', 'sí', '65 %', '86 %', '77 %'],
    ['Viene de frente a 3 m del costado', 'no', '96 %', '95 %', '95 %'],
    ['Viene de frente a 1 m del costado', 'sí', '100 %', '100 %', '100 %'],
    ['Camina delante, más rápido que el dron', 'no', '100 %', '100 %', '100 %'],
    ['Total (500 vuelos)', '', '91.2 %', '95.8 %', '94.0 %'],
]
filas_campo = [
    ['Escenario de campo', 'Repeticiones', 'Éxitos', 'IC Wilson 95 %', 'Latencia riesgo → comando (ms)',
     'Intervenciones del operador'],
    ['a) Panel de cartón, 1 m/s', '10', '[REVISAR: dato]', '', '', ''],
    ['a) Panel de cartón, 2 m/s', '10', '', '', '', ''],
    ['b) Maniquí quieto', '10', '', '', '', ''],
    ['c/e) Voluntario que se acerca caminando', '10', '', '', '', ''],
    ['d) Persona que cruza lejos', '10', '', '', '', ''],
]
h3 = f('3. Resultados', 550, 570)
seq(h3, [
    ('p', 'Los resultados se presentan en el orden de la Figura N4: primero la simulación del protocolo, después la '
          'comparación entre formas de decidir, luego las pruebas de banco y, al final, los ensayos de campo.'),
    ('h2', '3.1 Protocolo del comité en simulación'),
    ('p', 'Con el sistema activo, los 1300 vuelos del protocolo (13 variantes de 100 vuelos) terminaron con éxito: '
          '100.0 % [99.7, 100.0]. Sin el sistema, con el operador solo, apenas el 23 % [21, 25] de los vuelos fue '
          'seguro. Hubo 0 activaciones falsas en los 300 vuelos que no debían activarlo. El operador apretó la parada '
          'en 28 vuelos, todos con la persona que corre hacia el dron, y ninguno terminó en choque: con ese '
          'acercamiento el tope de 8 m deja menos de 2 s y un operador atento aprieta a la vez que el sistema. La '
          'Tabla N6 resume las latencias.'),
    ('tabla', 'Tabla N6', 'Latencias y distancias mínimas en simulación (100 vuelos por escenario)', filas_lat,
     [5.0, 3.6, 3.8, 3.4], 'Nota. Media e intervalo del 95 %. Fuente: simulacion/informes/minimo_tesis_protocolo.md.'),
    ('h2', '3.2 Decisión por reglas frente a decisión con IA'),
    ('p', 'En el protocolo del comité los cuatro decisores comparados (reglas, IA sola, IA con envolvente e IA con '
          'envolvente estricta) logran 100 % de éxito y ningún choque: los escenarios son claros y las reglas ya los '
          'resuelven. La diferencia aparece en los escenarios de discriminación (Tabla N7). La IA con envolvente acertó '
          'en 94.0 % [91.6, 95.8] de los vuelos, frente a 91.2 % [88.4, 93.4] de las reglas, y bajó las activaciones '
          'innecesarias de 44 a 30 en 1800 vuelos. En los vuelos en que los dos decisores difieren, la IA acierta y '
          'las reglas fallan 16 veces, y al revés 2 veces (McNemar, p = 0.0013).'),
    ('tabla', 'Tabla N7', 'Éxito por escenario de discriminación (100 vuelos cada uno)', filas_disc,
     [5.6, 2.4, 2.2, 2.2, 2.6], 'Nota. Fuente: simulacion/informes/minimo_tesis_decisor_ia.md.'),
    ('p', 'En 3840 vuelos sobre 60 mundos aleatorios que no se usaron ni para entrenar ni para elegir el umbral, la IA '
          'con envolvente redujo los vuelos con una persona a menos de 2 m por debajo de 3.30 m de 420 a 218 y las '
          'activaciones innecesarias de 137 a 67; los choques pasaron de 39 a 28, una diferencia que no es '
          'estadísticamente significativa. Ninguna cifra llega a cero porque ese conjunto incluye casos físicamente '
          'imposibles, como un panel a pocos metros con el dron a 8 m/s.'),
    ('p', 'Lo que no mejora: con el piloto a 4 m/s o menos (la velocidad recomendada), la IA con envolvente deja 24 '
          'riesgos sin evitar frente a 22 de las reglas, prácticamente lo mismo. En la operación recomendada la ventaja '
          'más clara de la IA es la eficiencia (menos detenciones innecesarias), no una seguridad mayor.'),
    ('h2', '3.3 Condiciones degradadas y velocidad máxima segura'),
    ('p', 'A las velocidades del protocolo ninguna degradación realista hizo fallar al sistema: pérdida de detecciones '
          '(recall 0.85 y 0.70), oclusión de medio cuerpo o del torso, ruido del LiDAR, latencias de 200 y 300 ms y '
          'viento de cola de 3 y 5 m/s. Los límites aparecen al subir la velocidad: el sistema se detiene con margen '
          'hasta 11 m/s frente al panel (lo limita el alcance útil del LiDAR), hasta 4 m/s frente a una persona quieta '
          'con reglas y hasta 12 m/s con la IA (porque la IA puede detener antes de los 8 m), y entre 7 y 10 m/s frente '
          'a una persona que corre, según la latencia. Con solo la cabeza y los hombros visibles la detección llega '
          'tarde incluso a 1 m/s: el sistema necesita ver al menos un tercio del cuerpo.'),
    ('h2', '3.4 Pruebas en banco'),
    ('rev', 'escribir con los registros de los pasos 1 a 5 del plan físico: cuadros por segundo sostenidos en 10 '
            'minutos, huecos del LiDAR, latencia riesgo → comando medida en el registro, retoma del piloto con CH5, y '
            'comparación del decisor en modo sombra con la simulación. Incluir fotos del montaje'),
    ('h2', '3.5 Ensayos de campo'),
    ('tabla', 'Tabla N8', 'Resultados de campo por escenario', filas_campo, [4.4, 2.0, 1.8, 2.4, 2.8, 2.6],
     'Nota. Llenar con el registro de la Jetson y el DataFlash de ArduPilot. [REVISAR: incluir fecha, hora, viento '
     'medido e iluminación de cada jornada]'),
    ('h2', '3.6 Discusión'),
    ('rev', 'la plantilla trae la discusión como capítulo aparte; aquí basta una sección. Comparar cada fila de campo '
            'con la simulación (si la tasa cae dentro del intervalo de la simulación, decirlo; si no, explicar qué '
            'diferencia la causa: sensor, latencia o viento) y comparar con los antecedentes de 1.5 (por ejemplo, la '
            'brecha entre simulación y vuelo real que señalan Vera-Yanez et al., 2023)'),
])

# =====================================================================
# 13. Conclusiones y recomendaciones
# =====================================================================
marcar(P[560])
revisar(P[560], 'este párrafo cuenta un hecho del desarrollo, no una conclusión; ya está en 2.2.5')
seq(P[561], [
    ('p', 'Primer objetivo (arquitectura). Se definió una arquitectura de percepción, decisión y control con un detector '
          'YOLO preentrenado, un LiDAR frontal, una computadora de a bordo Jetson Orin Nano y una controladora Pixhawk. '
          'La selección por matrices de decisión eligió al principio una Raspberry Pi; las pruebas de integración '
          'mostraron que su capacidad estaba sobreestimada y se cambió a la Jetson. [REVISAR: cerrar con la latencia '
          'total medida]'),
    ('p', 'Segundo objetivo (integración). Se verificaron en el dron la activación (arranque con alimentación propia y '
          'detección continua), la comunicación (LiDAR a 100 Hz y MAVLink a 115200 baudios con confirmación) y la '
          'respuesta del detector ante personas en movimiento. [REVISAR: agregar el cambio a GUIDED y la retoma del '
          'piloto cuando se prueben en banco]'),
    ('p', 'Tercer objetivo (validación). En simulación el protocolo se cumplió en el 100 % de 1300 vuelos, y la '
          'decisión con IA dentro de reglas fue más precisa que las reglas solas en los casos dudosos (94.0 % frente a '
          '91.2 %, p = 0.0013), sin perder seguridad. [REVISAR: conclusión de campo con la Tabla N8]'),
    ('p', '[REVISAR: una conclusión general de uno o dos párrafos, que responda la pregunta de investigación de 1.3]'),
])
p5 = f('5. Recomendaciones', 550, 600)
seq(p5, [
    ('li', 'Instalar un filtro IR-cut en la cámara antes de los ensayos con sol: sin él la imagen muestra una '
           'cuadrícula de manchas y un tinte morado.'),
    ('li', 'Ampliar los ensayos de campo a 35 repeticiones por escenario si se quiere afirmar un éxito de al menos 90 % '
           'con 95 % de confianza.'),
    ('li', 'Reentrenar el clasificador mezclando datos reales y simulados si en modo sombra decide distinto que en '
           'simulación.'),
    ('li', 'Antes de mover el LiDAR al chasis o de agregar un segundo LiDAR en el estabilizador, repetir la simulación '
           'del protocolo con la nueva geometría: el clasificador se entrenó con el TF03 alineado con la cámara a −5°.'),
    ('li', 'Evaluar si el ascenso de protección debe esperar la autorización del árbitro: por encima de 4 m/s ese veto '
           'es la principal fuente de aproximaciones a menos de 2 m (decisión D-048, abierta).'),
    ('li', 'Como trabajo futuro, la política de seguimiento entrenada por refuerzo (PPO) que se desarrolló en paralelo '
           'en simulación puede extender el sistema a la búsqueda y el seguimiento de una persona designada por el '
           'operador; queda fuera del alcance aprobado.'),
    ('li', 'Probar el lazo MAVLink completo en el simulador SITL de ArduPilot antes de cada cambio de software.'),
])

# =====================================================================
# 14. Referencias
# =====================================================================
marcar(f('Ahmed, N., Raza, A.', 560, 600))
revisar(f('Ahmed, N., Raza, A.', 560, 600), 'es el mismo artículo que Kurunathan et al.; la autoría correcta es la de '
        'Kurunathan. Las citas del texto ya se cambiaron')
qk = f('Kurunathan, H., Huang, H.', 560, 600)
marcar(qk)
qk2 = par_after(D, qk, 'Kurunathan, H., Huang, H., Li, K., Ni, W., & Hossain, E. (2024). Machine learning-aided operations '
                'and communications of unmanned aerial vehicles: A contemporary survey. IEEE Communications Surveys & '
                'Tutorials, 26(1), 496–533. https://doi.org/10.1109/COMST.2023.3312221', VERDE)
revisar(qk2, 'el DOI y los datos del Word (2022, 24(4), 2554–2597) no corresponden a este artículo: salió en arXiv en 2022 '
             'y en la revista en 2024. Confirmar el DOI con un clic')
for autor in ('Jiang, P., Ergu, D.', 'Lahmeri, M.-A.', 'Palossi, D., Zimmerman', 'ArduPilot. (s. f.-b)'):
    q = f(autor, 560, 600)
    marcar(q)
    revisar(q, 'no se cita en ninguna parte del texto; la plantilla exige que toda referencia esté citada al menos '
               'una vez. Citarla donde corresponda o quitarla')
p = f('PX4 Autopilot. (s. f.)', 560, 600)
revisar(p, 'el texto cita "(PX4, 2025)" y aquí dice "(s. f.)": unificar. Se limpió del enlace el sufijo '
           '"?utm_source=chatgpt.com"')
rel_fix = 0
for rel in D.d.part.rels.values():
    if rel.is_external and 'utm_source' in rel._target:
        rel._target = re.sub(r'[?&]utm_source=[^&]*', '', rel._target)
        rel_fix += 1
nuevas = [
    'ArduPilot. (s. f.-c). Loiter mode. ArduPilot Copter Documentation. https://ardupilot.org/copter/docs/loiter-mode.html',
    'ArduPilot. (s. f.-d). Guided mode. ArduPilot Copter Documentation. https://ardupilot.org/copter/docs/ac2_guidedmode.html',
    'Benewake. (s. f.). TF03-180 datasheet (V1.2). https://en.benewake.com/TF03/index.html',
    'Brand, T. (2021, 1 de febrero). Time of flight system for distance measurement and object detection. Analog Devices. '
    'https://www.analog.com/en/resources/technical-articles/tof-system-for-distance-measurement-and-object-detection.html',
    'Chaumette, F., & Hutchinson, S. (2006). Visual servo control, part I: Basic approaches. IEEE Robotics & Automation '
    'Magazine, 13(4), 82–90. [REVISAR: agregar el DOI desde IEEE Xplore]',
    'Congreso de la República de Colombia. (2012, 17 de octubre). Ley Estatutaria 1581 de 2012: Por la cual se dictan '
    'disposiciones generales para la protección de datos personales (Diario Oficial n.° 48.587). '
    'https://normograma.mintic.gov.co/mintic/compilacion/docs/ley_1581_2012.htm',
    'Falanga, D., Mueggler, E., Faessler, M., & Scaramuzza, D. (2017). Aggressive quadrotor flight through narrow gaps '
    'with onboard sensing and computing using active vision. En 2017 IEEE International Conference on Robotics and '
    'Automation (ICRA) (pp. 5774–5781). IEEE. https://doi.org/10.1109/ICRA.2017.7989679',
    'Gallo Sanabria, J. D., Mozuca Tamayo, P. A., & Rincón Fonseca, R. I. (2020). Autonomous trajectory following for an '
    'UAV based on computer vision. Visión Electrónica, 14(1), 51–56. https://doi.org/10.14483/22484728.15968',
    'Ministerio del Trabajo. (2015, 26 de mayo). Decreto 1072 de 2015: Por medio del cual se expide el Decreto Único '
    'Reglamentario del Sector Trabajo (Diario Oficial n.° 49.523). Función Pública. '
    'https://funcionpublica.gov.co/eva/gestornormativo/norma.php?i=72173',
    'Ultralytics. (s. f.). Ultralytics YOLO26. Ultralytics Docs. https://docs.ultralytics.com/models/yolo26/',
    'Unidad Administrativa Especial de Aeronáutica Civil. (2023). RAC 100: Operación de sistemas de aeronaves no '
    'tripuladas UAS (Resolución 01983 de 2023; enmienda 2 de diciembre de 2024). Aerocivil. [REVISAR: confirmar la fecha '
    'de la resolución; y en 1.8.2 cambiar "actualización más reciente el 24 de abril de 2024" si la enmienda 2 es la '
    'última]',
    'Valenti, F., Giaquinto, D., Musto, L., Zinelli, A., Bertozzi, M., & Broggi, A. (2018). Enabling computer '
    'vision-based autonomous navigation for unmanned aerial vehicles in cluttered GPS-denied environments. En 2018 21st '
    'International Conference on Intelligent Transportation Systems (ITSC) (pp. 3886–3891). IEEE. '
    'https://doi.org/10.1109/ITSC.2018.8569695',
    'McNemar, Q. (1947). Note on the sampling error of the difference between correlated proportions or percentages. '
    'Psychometrika, 12(2), 153–157. https://doi.org/10.1007/BF02295996',
    'Meisel Roca, A., & Vega Argote, M. (2007). La estatura de los colombianos: un ensayo de antropometría histórica, '
    '1910-2002. Banco de la República. [REVISAR: completar serie, número y URL]',
    'Pedregosa, F., Varoquaux, G., Gramfort, A., Michel, V., Thirion, B., Grisel, O., Blondel, M., Prettenhofer, P., '
    'Weiss, R., Dubourg, V., Vanderplas, J., Passos, A., Cournapeau, D., Brucher, M., Perrot, M., & Duchesnay, É. '
    '(2011). Scikit-learn: Machine learning in Python. Journal of Machine Learning Research, 12, 2825–2830.',
    'Pugh, S. (1991). Total design: Integrated methods for successful product engineering. Addison-Wesley.',
    'Rumelhart, D. E., Hinton, G. E., & Williams, R. J. (1986). Learning representations by back-propagating errors. '
    'Nature, 323(6088), 533–536. https://doi.org/10.1038/323533a0',
    'Ulrich, K. T., & Eppinger, S. D. (2016). Product design and development (6.ª ed.). McGraw-Hill Education.',
    'Wilson, E. B. (1927). Probable inference, the law of succession, and statistical inference. Journal of the '
    'American Statistical Association, 22(158), 209–212. https://doi.org/10.1080/01621459.1927.10502953',
]
ult = f('Vera-Yanez, D., Pereira', 560, 600)
ult = par_after(D, ult, '[REVISAR: entradas en amarillo verificadas por la sesión "Análisis de repositorios" con '
                'búsquedas web (probar cada DOI con un clic). Quedan incompletas y hay que completarlas desde el '
                'repositorio de cada universidad: Avilés Correa y Garzón Bernal (el año: "2019/2021" no es válido en '
                'APA; repository.libertadores.edu.co/handle/11371/4904), León Mondragón y Rojas Díaz (nombres y año, '
                'repositorio de la Universidad Distrital), Bohórquez Caro (2021) (nivel del trabajo y URL, Escuela '
                'Colombiana de Ingeniería) y el Convenio de Chicago (OACI, Doc 7300, edición y año). No se encontró '
                'ningún registro de Córdoba Velásquez y Ruiz Rincón (2023): buscarla en bibliotecadigital.usb.edu.co o '
                'quitarla del estado del arte. La plantilla recomienda manejar todo con Mendeley y ordenar '
                'alfabéticamente]', TURQ)
for t in nuevas:
    ult = par_after(D, ult, t, AMARILLO)

# =====================================================================
# 15. Anexos
# =====================================================================
anexos = [
    ('p', 'Organización propuesta de los anexos. Todo el código va aquí; en el cuerpo del documento solo quedan '
          'diagramas. Cada anexo empieza con un párrafo que dice qué hace el módulo, sus entradas y sus salidas, y '
          'luego el listado.'),
    ('li', 'Anexo A. Percepción: jetson/percepcion.py, jetson/lidar_tf.py, jetson/sensores.py y jetson/camara_csi.py.'),
    ('li', 'Anexo B. Decisión: simulacion/minimo_tesis/decisor_ia.py (evaluación del MLP con NumPy), la envolvente de '
           'reglas de simulacion/minimo_tesis/sistema.py y el archivo de pesos decision.json (resumido).'),
    ('li', 'Anexo C. Control y MAVLink: jetson/vuelo_evasion.py, jetson/intervencion_banco.py y jetson/config.py '
           '(sin direcciones IP, usuarios ni rutas internas).'),
    ('li', 'Anexo D. Simulación: simulacion/minimo_tesis/sensores.py, control.py, protocolo_comite.py y '
           'entrenar_decisor.py.'),
    ('li', 'Anexo E. Parámetros de ArduPilot: tabla de docs/pixhawk.md (enlace, modos, failsafe, gimbal) y los de '
           'la prueba (LOIT_SPEED, LOIT_BRK_ACCEL, GUID_TIMEOUT, geocerca).'),
    ('li', 'Anexo F. Protocolo de pruebas: lista de verificación previa, planilla por repetición, consentimiento de '
           'imagen de los voluntarios (Ley 1581 de 2012) y plano del campo con las marcas de 2 a 15 m.'),
    ('rev', 'según la plantilla, en la tabla de contenido solo va el título "Anexos"; los títulos "Anexo A…" y "A.0…" '
            'no deben aparecer ahí (darles un estilo que no sea de título, o quitarlos del índice)'),
    ('rev', 'los apartados A.0 a A.3 actuales describen una versión anterior (con paneo del cardán); reacomodarlos en '
            'los anexos A a C. Confirmar con la norma de la universidad si los anexos cuentan dentro de las 100 '
            'páginas'),
]
seq(P[-1], anexos)

D.d.save(SALIDA)
print('Listo:', SALIDA)
print('Enlaces corregidos:', rel_fix)
print('\n'.join(LOG) or 'Sin reemplazos de respaldo')
