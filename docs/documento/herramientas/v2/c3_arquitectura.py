"""Capítulo 2 · 2.1 Definición de la arquitectura operacional."""
import math

from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph

from motor import AMARILLO, ROJO, TURQ, ROSA, VERDE


def celda(M, tabla, fila, col, nuevo):
    """Texto de una celda: el viejo en rojo y el nuevo en verde."""
    import copy
    from docx.text.run import Run
    c = tabla.cell(fila, col)
    par = c.paragraphs[0]
    rpr = None
    for p in c.paragraphs:
        for r in p._p.iter(qn('w:r')):
            if rpr is None and r.find(qn('w:rPr')) is not None:
                rpr = copy.deepcopy(r.find(qn('w:rPr')))
                for e in rpr.findall(qn('w:highlight')):
                    rpr.remove(e)
            Run(r, None).font.highlight_color = ROJO
    if nuevo:
        M.texto(par, ' ' + nuevo if par.text.strip() else nuevo, VERDE, rpr=rpr)


def aplicar(M, reescribir, mover, DIAG):
    P, T = M.P, M.T
    claves = {372: None, 373: ('Tabla', 'req'), 377: ('Figura', 'caja_negra'), 380: ('Figura', 'caja_transp'),
              386: ('Figura', 'funcional'), 409: ('Tabla', 'comb'), 417: ('Tabla', 'pasa'), 423: ('Tabla', 'pesos'),
              426: ('Tabla', 'f1'), 433: ('Tabla', 'f2'), 440: ('Tabla', 'f3'), 441: ('Tabla', 'concepto'),
              394: ('Tabla', 'gen'), 398: ('Tabla', 'juicios'), 406: ('Tabla', 'filtrado'),
              442: ('Figura', 'conceptofig'), 457: ('Tabla', 'qfd')}
    for i, k in claves.items():
        if k:
            M.claves[P[i]._p] = k

    for tb in M.T:
        filas = tb._tbl.findall(qn('w:tr'))
        if len(filas) == 6 and not ''.join(x.text or '' for x in filas[0].iter(qn('w:t'))).strip() and \
                'Concepto Global' in ''.join(x.text or '' for x in filas[1].iter(qn('w:t'))):
            tb._tbl.remove(filas[0])     # la tabla de combinación de conceptos traía una fila vacía arriba
            break
    reescribir([368], [
        'El desarrollo de ingeniería se organiza en tres bloques, uno por objetivo específico. El primero define la '
        'arquitectura operacional y selecciona los componentes (2.1). El segundo integra el sistema en el cuadricóptero '
        'y programa la lógica de evasión (2.2). El tercero define el protocolo de validación en un entorno exterior '
        'controlado y el origen de cada valor numérico del sistema (2.3).'])
    reescribir([370], [
        'Para el primer objetivo se siguió una ruta de diseño conceptual. Se definieron los requerimientos funcionales '
        '(2.1.1) y se analizaron las funciones del sistema con diagramas de caja negra, caja transparente y funcional '
        '(2.1.2). Después se generaron alternativas para cada función (2.1.3), se juzgó su viabilidad (2.1.4) y se '
        'filtraron (2.1.5); las que quedaron se combinaron en conceptos globales (2.1.6) y se compararon con una matriz '
        'pasa/no pasa (2.1.7). Los componentes se seleccionaron con una matriz de decisión ponderada (2.1.8), los '
        'requerimientos se tradujeron en especificaciones con un despliegue de la función de calidad (2.1.9) y el '
        'umbral de seguridad del LiDAR se justificó en 2.1.10. El Anexo B reúne la prueba de sensibilidad de la escala '
        'de calificación y la revisión de la selección con datos medidos.'])

    # ---------------- 2.1.1 requerimientos
    reescribir([372], [
        'Los requerimientos funcionales salen de los objetivos del proyecto y fijan lo que el sistema debe cumplir para '
        'detectar personas y obstáculos, identificar una proximidad crítica y activar una maniobra básica de evasión en '
        'exteriores. Se clasifican en hardware, software y operación ({T:req}), para separar lo que se instala en la '
        'aeronave, lo que resuelve la computadora de a bordo y las condiciones en que se valida el sistema.'])
    t1 = T[2]
    nuevos = {
        1: ('Capturar video continuo del frente del cuadricóptero con luz natural variable.',
            'Es la entrada del detector de personas; sin ella no hay detección.'),
        2: ('Ejecutar un detector preentrenado que identifique personas en cada cuadro.',
            'Indica si lo que hay al frente es una persona, dato que cambia la respuesta del sistema.'),
        3: ('Medir la distancia frontal con un sensor LiDAR de tiempo de vuelo.',
            'Da una distancia directa que no depende de la iluminación ni del deslumbramiento solar.'),
        4: ('Procesar imagen, distancia y decisión en la propia aeronave.',
            'Evita la latencia de enviar video a tierra y separa este cómputo de la controladora.'),
        5: ('Enviar las órdenes de la computadora a la controladora por MAVLink.',
            'Convierte la decisión en una orden que el autopiloto entiende.'),
        6: ('Anular por un momento el avance del piloto y ordenar detención y ascenso vertical.',
            'Es la acción que evita la colisión dentro del margen vertical seguro.'),
        7: ('Alimentar la computadora y los sensores con una línea regulada e independiente.',
            'Evita reinicios de la computadora por caídas de tensión cuando los motores aceleran.'),
        8: ('Mantener la estabilidad y la detección con viento y alta luminosidad.',
            'Permite repetir el experimento en condiciones reales al aire libre.'),
        9: ('Registrar automáticamente tiempos, distancias, cuadros por segundo y órdenes enviadas.',
            'Aporta los datos para calcular la tasa de éxito, la latencia y las demás métricas.'),
        10: ('No recalcular rutas ni desplazarse de lado (sin navegación autónoma).',
             'Mantiene el alcance acordado: protección frontal con respuesta vertical.'),
        11: ('Devolver el control al piloto si el programa se bloquea o se pierde el enlace.',
             'Evita vuelos sin control ante una falla del software.'),
    }
    for fila, (desc, just) in nuevos.items():
        celda(M, t1, fila, 3, desc)
        celda(M, t1, fila, 4, just)
    celda(M, t1, 2, 1, 'Detección de personas')
    celda(M, t1, 10, 1, 'Delimitación de la respuesta')

    # ---------------- 2.1.2 análisis funcional (figuras redibujadas)
    reescribir([376], [
        'El análisis funcional parte del método de caja negra, que define qué entra y qué sale del sistema sin detallar '
        'cómo funciona por dentro ({F:caja_negra}). Las entradas son las necesidades de la misión: detectar personas y '
        'obstrucciones, integrar percepción, decisión y control, y operar en un entorno exterior controlado. Las salidas '
        'son los productos que responden a ellas: una arquitectura operativa definida, un módulo de decisión y '
        'comunicación integrado y un protocolo de evasión validado.'])
    for img_i, nombre in ((378, '06_caja_negra'), (381, '07_caja_transparente'), (387, '08_funcional')):
        M.marcar(P[img_i])
        M.figura(P[img_i], f'{DIAG}/{nombre}.png', color=VERDE)
    reescribir([379], [
        'La caja transparente muestra los subsistemas internos ({F:caja_transp}). La batería alimenta, a través del Power '
        'Module, a la placa de distribución y a la Pixhawk; de la placa sale un convertidor buck que entrega 12 V a la '
        'Jetson. La cámara USB y el LiDAR TF03 captan el entorno. En la Jetson, YOLO26n detecta personas, el '
        'clasificador de riesgo estima si hay peligro y las reglas de seguridad deciden la orden final, que llega a la '
        'Pixhawk por MAVLink. La controladora estabiliza la aeronave, atiende al piloto y ejecuta la maniobra. El sistema '
        'produce dos salidas: la respuesta física (detención y ascenso) y el registro de datos para la evaluación.'])
    reescribir([383], [
        'El diagrama funcional descompone el objetivo general en tres funciones ({F:funcional}). F1 percibe el frente de '
        'la aeronave: capta video con luz natural variable y mide la distancia frontal de forma directa. F2 procesa y '
        'decide a bordo: alimenta la computadora con una línea regulada propia y detecta personas y estima el riesgo en '
        'tiempo real. F3 responde con seguridad: envía la orden a la controladora, detiene el avance y asciende, y '
        'devuelve el mando al piloto o activa el failsafe cuando hace falta.'])
    for i in (382, 384, 385, 388, 389):
        M.marcar(P[i])
    M.parrafo(P[388], '[REVISAR: las Figuras de caja negra, caja transparente y diagrama funcional se redibujaron con '
                      'los componentes reales. La original de caja transparente decía Raspberry Pi, cámara CSI y UBEC de '
                      '5 V y repetía un bloque; la funcional repetía dos subfunciones de F1 dentro de F2]', TURQ)

    # ---------------- 2.1.3 a 2.1.5: se conservan las tablas del diseño
    reescribir([391, 392, 393], [
        'Para cada subfunción se listaron las alternativas tecnológicas razonables, agrupadas en tres bloques: '
        'percepción y telemetría en exteriores, procesamiento y decisión a bordo, y control y seguridad de vuelo '
        '({T:gen}). La plataforma aérea (el cuadricóptero del semillero Aerosant), la unidad de procesamiento y la '
        'controladora Pixhawk se tomaron como condiciones iniciales por disponibilidad institucional; la cámara, el '
        'sensor de distancia y el modelo de inteligencia artificial se sometieron a comparación. La unidad de '
        'procesamiento prevista al inicio, una Raspberry Pi 4, se reemplazó después por una NVIDIA Jetson Orin Nano '
        'por las razones expuestas en 2.2.5.'])
    reescribir([396, 397], [
        'Cada alternativa recibió un juicio de viabilidad en cuatro niveles (alta viabilidad, viabilidad moderada, '
        'riesgo medio y riesgo crítico), según la dificultad de adquirirla, su desempeño esperado y su flexibilidad, y '
        'teniendo en cuenta la masa, el consumo eléctrico, el ruido y la exposición al clima. La {T:juicios} reúne las '
        'subfunciones críticas con el juicio de cada concepto y la razón técnica que lo sustenta.'])
    reescribir([401, 402, 403, 404, 405], [
        'Con los juicios se recortaron los conceptos que no aportan al proyecto, con dos criterios. El primero son los '
        'aportes positivos y negativos de cada elemento: se descartaron los que sumaban más factores negativos, como '
        'masa excesiva, latencia alta o consumo desproporcionado. El segundo es la disposición para operar en '
        'exteriores: se descartaron los vulnerables al viento o a la luz solar directa. La {T:filtrado} muestra el '
        'resultado, una preselección de tecnologías aptas para la misión al aire libre.'])

    # ---------------- 2.1.4 combinación y 2.1.5 pasa/no pasa
    reescribir([408], [
        'Las alternativas que superaron el filtro se agruparon en tres conceptos globales, cada uno con una opción de '
        'procesamiento, percepción visual, telemetría y gestión eléctrica ({T:comb}). Agruparlas permite ver cómo '
        'interactúan los componentes antes de compararlos.'])
    reescribir([411], [
        'Los tres conceptos se evaluaron con una matriz pasa/no pasa ({T:pasa}). "Pasa" indica que el concepto cumple un '
        'requerimiento indispensable para operar al aire libre con seguridad; "no pasa" señala una limitación crítica, '
        'como exceso de masa, de consumo o vulnerabilidad al clima, que descarta el concepto.'])
    reescribir([412], [
        'El concepto 1 no pasa en estabilidad de potencia y masa: una GPU de alto consumo (Jetson Nano) con una batería '
        'secundaria excede la carga útil y el consumo admisibles. El concepto 3 no pasa ningún criterio crítico: un '
        'microcontrolador no puede ejecutar redes neuronales a bordo y los sensores ultrasónicos fallan con el viento. '
        'El concepto 2 pasa todos los criterios, con una Raspberry Pi, un LiDAR, un regulador UBEC y compatibilidad con '
        'las rutinas de fallo seguro, y fue el elegido para la evaluación cuantitativa.'])
    for i in (413, 414, 415, 416):
        M.marcar(P[i])

    # ---------------- 2.1.6 matriz ponderada
    reescribir([419], [
        'Los componentes se seleccionaron con una matriz de decisión ponderada basada en el método de Pugh (Pugh, '
        '1991). Cada alternativa se calificó de 1 a 10 frente a los requerimientos y cada calificación se multiplicó por '
        'el peso del requerimiento.'])
    M.marcar(P[420])
    reescribir([421], [
        'Los pesos expresan qué tan crítico es cada requerimiento para el vuelo al aire libre ({T:pesos}). De 1 a 3 '
        'corresponden a características prescindibles; de 4 a 7, a funciones útiles que no condicionan la seguridad; y '
        'de 8 a 10, a funciones de las que dependen la seguridad o la existencia del sistema. La gestión de potencia y '
        'masa (RF-07) recibió 8: aislar la alimentación de la computadora es indispensable, pero es un respaldo físico. '
        'La telemetría de proximidad (RF-03), el enlace MAVLink (RF-05/RF-06) y la tolerancia al viento con failsafe '
        '(RF-08/RF-11) recibieron 9, porque una falla en cualquiera de ellos termina en colisión. La percepción visual '
        '(RF-01/RF-02) y el procesamiento a bordo (RF-04) recibieron 10: sin ellos el sistema no existe.'])
    q_esc = M.parrafo(T[8]._tbl, 'La escala de 1 a 10 se eligió por su resolución. Con 1 a 5, alternativas cercanas de una '
                      'misma subfunción quedarían empatadas; con 10 niveles se distinguen. Cada nivel tiene una '
                      'descripción concreta ({T:escala}), y la selección no cambia si las calificaciones se pasan a una '
                      'escala de 1 a 5 (Anexo B, {T:tB5}) (Pugh, 1991; Ulrich & Eppinger, 2016).', AMARILLO)
    from datos_tablas import ANCLAS
    cap_esc = M.rotulo(q_esc, 'Tabla', 'escala', 'Significado de cada nivel de la escala de 1 a 10')
    M.tabla(cap_esc, ANCLAS, [1.3, 4.9, 4.9, 4.9])
    reescribir([424], [
        'La {T:f1} califica los sensores visuales y de distancia según su capacidad y su robustez al aire libre: el 1 '
        'corresponde a un sensor inoperante en exteriores y el 10 a una percepción rápida, estable y con alta inmunidad a '
        'la luz solar. Los pesos de cada criterio aparecen entre paréntesis y el total es la suma de calificación por '
        'peso.'])

    pesos8 = [10, 9, 9, 8, 9]
    pesos9 = [10, 10, 8, 8, 9]

    def recalcular(tabla, pesos, nombres_peso):
        filas = len(tabla.rows)
        cols = len(tabla.columns)
        for fi in range(1, filas - 1):
            nombre = tabla.cell(fi, 0).text.strip()
            pr = tabla.cell(fi, 0).paragraphs[0]
            r0 = pr._p.find(qn('w:r'))
            rp = r0.find(qn('w:rPr')) if r0 is not None else None
            M.texto(pr, f' (peso {pesos[fi - 1]})', VERDE, rpr=rp)
        for cj in range(1, cols):
            vals = []
            for fi in range(1, filas - 1):
                v = tabla.cell(fi, cj).text.strip()
                vals.append(int(v) if v.isdigit() else 0)
            total = sum(a * b for a, b in zip(vals, pesos))
            celda(M, tabla, filas - 1, cj, str(total))

    recalcular(T[9], pesos8, True)
    recalcular(T[10], pesos9, True)
    reescribir([427], ['Dentro de las cámaras, la CSI nativa obtiene el mayor puntaje (315), por encima de la web USB (225) '
                       'y de la cámara de acción (127). Entre los sensores de distancia, el LiDAR de tiempo de vuelo (306) '
                       'supera al radar mmWave (248) y al ultrasónico (127). Se descartaron:'])
    reescribir([428], ['Cámara de acción (GoPro): no tiene un bus de baja latencia hacia la computadora de a bordo, lo '
                       'que retrasa la captura.'])
    reescribir([429], ['Cámara web USB: se consideró que cargaba la CPU de la Raspberry Pi y añadía latencia. Con la '
                       'Jetson esa limitación no apareció y fue la cámara que finalmente se usó (2.2.5).'])
    reescribir([430], ['Sensor ultrasónico: el viento y el ruido de los motores atenúan el eco y producen lecturas '
                       'perdidas y falsos positivos.'])
    reescribir([431], ['Radar mmWave: su masa y la complejidad de su software superan lo que permite el tiempo de '
                       'desarrollo, frente a un LiDAR.'])
    reescribir([432], [
        'La {T:f2} califica el procesamiento, los modelos de detección y la alimentación, comparando la capacidad de '
        'cómputo con la masa y el consumo: el 1 corresponde a un elemento sin sistema operativo embebido y el 10 a una '
        'integración completa, con procesamiento fluido y alimentación aislada.'])
    reescribir([434], ['Entre los procesadores, la Raspberry Pi 4 obtiene 378 puntos, por encima de la Jetson Nano (351) y del '
                       'Teensy 4.1 (193); entre los modelos, YOLO nano (333) supera a EfficientDet y MobileNet (249); y '
                       'entre las soluciones de potencia, el regulador UBEC dedicado (152) supera a una batería '
                       'secundaria (80). Se descartaron:'])
    reescribir([435], ['Jetson Nano: por su consumo (hasta 4 A de pico) y su masa. Esta calificación se revisó después '
                       'con datos medidos, como se explica más adelante.'])
    reescribir([436], ['Teensy 4.1: no tiene sistema operativo ni memoria suficiente para ejecutar redes neuronales '
                       'convolucionales.'])
    reescribir([437], ['EfficientDet-Lite y MobileNet: en CPU logran menos cuadros por segundo que las versiones '
                       'compactas de YOLO.'])
    reescribir([438], ['Batería secundaria: añade masa que reduce la sustentación y el tiempo de vuelo.'])
    reescribir([439], [
        'La {T:f3} califica la integración de la lógica de decisión con la plataforma de vuelo según su confiabilidad: '
        'el 1 corresponde a una integración bloqueada por un sistema cerrado y el 10 a un control total, con rutinas de '
        'fallo seguro mediante protocolos estándar. Las alternativas cumplen papeles distintos (controladora, protocolo '
        'y plataforma), así que los totales solo se comparan dentro de cada papel.'])

    # Tabla 10 rehecha (la original repetía la Tabla 9)
    t10 = T[11]
    celda(M, t10, 0, 4, 'Intervención por PWM')
    criterios = ['Integración con la computadora de a bordo (RF-04, peso 10)',
                 'Enlace y ejecución de la maniobra (RF-05/RF-06, peso 9)',
                 'Fallo seguro y tolerancia (RF-08/RF-11, peso 9)',
                 'Masa y potencia (RF-07, peso 8)', '', 'Puntaje total ponderado']
    cal = {1: [9, 10, 10, 9], 2: [6, 8, 7, 7], 3: [9, 10, 9, None], 4: [4, 2, 2, 8], 5: [8, None, None, 8],
           6: [1, None, None, 9]}
    pes = [10, 9, 9, 8]
    for fi in range(1, 7):
        celda(M, t10, fi, 0, criterios[fi - 1] if fi < 5 else ('' if fi == 5 else criterios[5]))
    for cj, vals in cal.items():
        for fi, v in enumerate(vals, start=1):
            celda(M, t10, fi, cj, 'NA' if v is None else str(v))
        celda(M, t10, 5, cj, '')
        celda(M, t10, 6, cj, str(sum((v or 0) * w for v, w in zip(vals, pes))))
    nota10 = M.nota(t10._tbl, 'Nota. Calificaciones asignadas con la escala anclada de la {T:escala}. Se comparan '
                              'entre sí la Pixhawk y la Navio2 (controladora), MAVLink y la intervención por PWM '
                              '(protocolo) y el dron Aerosant frente a un dron comercial cerrado (plataforma). NA: no '
                              'aplica. [FALTA: validar estas calificaciones con el asesor]')
    M.parrafo(nota10, '[REVISAR: la Tabla 10 original era una copia de la Tabla 9 (mismas filas y números). Se rehízo con '
                      'criterios de control de vuelo y los pesos de la Tabla 7. En las Tablas 8 y 9 se agregaron los '
                      'pesos y se recalcularon los totales, porque los originales no salían de los pesos publicados; el '
                      'orden de las alternativas no cambió]', TURQ)
    p_reval = M.parrafo(nota10, 'Entre las controladoras, la Pixhawk (342) supera a la Navio2 (251); entre los protocolos, '
                        'MAVLink (261) supera a la intervención por PWM (140); y entre las plataformas, el dron Aerosant '
                        '(144) supera al comercial cerrado (82). La selección se revisó con los datos de la integración. La {T:f2} calificó la Raspberry '
                        'Pi 4 con 8 en inferencia, latencia y estabilidad de potencia, y descartó la Jetson Nano por '
                        'consumo y masa. En las pruebas de 2.2.5 la Raspberry Pi tuvo caídas de tensión, fallos de '
                        'arranque que corrompieron el sistema operativo y un cuello de botella en la inferencia; la '
                        'Jetson Orin Nano, una generación posterior a la Jetson Nano evaluada, procesa cada cuadro en 9 a '
                        '11 ms con TensorRT y no se reinició con su convertidor de 12 V. Con esas calificaciones medidas '
                        'la selección se invierte (Anexo B, {T:tB6}). La matriz cumplió su función con la información '
                        'disponible; lo que falló fue la calificación supuesta de la Raspberry Pi, que solo se pudo '
                        'corregir midiendo. La {T:concepto} resume el concepto global que salió de la matriz.', AMARILLO)
    # concepto global y comparación con lo implementado
    filasN1 = [
        ['Subsistema', 'Concepto del diseño', 'Implementado', 'Motivo del cambio'],
        ['Computación de a bordo', 'Raspberry Pi 4 Model B', 'NVIDIA Jetson Orin Nano', 'Caídas de tensión, fallos de '
         'arranque y cuello de botella en la inferencia (2.2.5)'],
        ['Cámara', 'Cámara nativa CSI', 'Cámara web USB 640×480, 30 cuadros/s, HFOV 38.9°',
         'La cámara CSI IMX219 daba pantallas verdes y bloqueaba su servicio'],
        ['LiDAR', 'TF-Luna', 'Benewake TF03 (UART por USB-TTL), 100 Hz', 'Alcance de hasta 70 m sobre superficies '
         'oscuras, frente a unos 8 m del TF-Luna'],
        ['Detector', 'YOLO versión nano', 'YOLO26n en TensorRT FP16, 9–11 ms por cuadro', 'Aceleración por GPU'],
        ['Decisión', 'Lógica de umbrales críticos', 'Clasificador MLP dentro de reglas de seguridad',
         'Menos detenciones innecesarias con la misma seguridad (capítulo 3)'],
        ['Potencia lógica', 'UBEC 5 V / 3 A', 'Convertidor buck a 12 V para la Jetson', 'La Jetson consume más y '
         'necesita su propia línea (RF-07)'],
        ['Enlace', 'MAVLink por UART', 'MAVLink 2 por TELEM2 a 115200 baudios', 'A 460800 y 921600 baudios la '
         'Pixhawk no entendía a la Jetson'],
        ['Estabilizador', '—', 'BaseCam de 2 ejes, inclinación fija −5° por PWM desde AUX1', 'El firmware no obedece '
         'órdenes por puerto serie'],
        ['Posicionamiento', '—', 'GPS de la Pixhawk', 'El modo GUIDED exige posición GPS en exteriores'],
    ]
    t11 = T[12]
    p_n1 = M.parrafo(t11._tbl, 'Ese concepto global cambió en la integración. La '
                     '{T:implementado} compara cada subsistema diseñado con el que finalmente se instaló y explica por '
                     'qué.', AMARILLO)
    cap = M.rotulo(p_n1, 'Tabla', 'implementado', 'Concepto global diseñado frente al implementado')
    tN1 = M.tabla(cap, filasN1, [3.0, 3.2, 4.6, 5.2])
    # figuras 20 a 22
    M.parrafo(tN1, 'El concepto global del diseño, antes de los cambios de la integración, se muestra en la '
                   '{F:conceptofig}.', AMARILLO)
    M.marcar(P[443])
    fig_c = M.figura(P[443], f'{DIAG}/12_concepto.png', ancho_cm=15.5, color=VERDE)
    M.nota(fig_c, 'Nota. Corresponde al concepto del diseño, con Raspberry Pi, cámara CSI y TF-Luna. El concepto '
                  'implementado está en la {T:implementado}.')
    M.parrafo(fig_c, '[REVISAR: el diagrama original tenía texto ilegible; se redibujó con los componentes del concepto '
                     'de la tabla anterior]', TURQ)
    for i in (444, 445, 446, 447, 448, 449, 450, 451):
        M.marcar(P[i])
    M.parrafo(P[451], '[REVISAR: las Figuras 21 y 22 se eliminaron: fueron generadas con IA y tenían datos falsos '
                      '(motores A2212 de 1000 KV y "Jetson Nano"; el dron usa motores 2212-920 KV y una Jetson Orin '
                      'Nano). La foto real del dron está en 2.2.1. El diagrama del concepto del diseño se conserva en este apartado]',
              TURQ)

    # ---------------- 2.1.7 QFD
    reescribir([453, 454, 455, 456], [
        'Para traducir los requerimientos en especificaciones medibles se aplicó un despliegue de la función de calidad '
        '(QFD) simplificado. El usuario directo es el semillero de investigación Aerosant y el programa de Ingeniería '
        'Aeronáutica de la Universidad de San Buenaventura. A partir de los objetivos se fijaron siete requerimientos '
        'operativos: detección visual confiable de personas y obstáculos, medición directa de la distancia frontal, '
        'procesamiento a bordo sin enlaces de video, activación oportuna de la maniobra vertical, alimentación aislada '
        'de los motores, recuperación inmediata del control manual y registro automático de datos. Su importancia '
        'relativa, de 1 a 10, está en la {T:qfd}.'])
    M.parrafo(T[13]._tbl, 'Esos requerimientos se tradujeron en ocho especificaciones de ingeniería: frecuencia de muestreo '
              'del LiDAR (Hz), cuadros por segundo de la inferencia, latencia del lazo sensor–decisión–actuador (ms), masa '
              'añadida (g), corriente del sistema embebido (A), rizado de la línea de alimentación (mV), distancia umbral '
              'de activación (m) y tiempo de respuesta ante la pérdida del enlace serie (ms). La matriz de la casa de la '
              'calidad mostró una relación fuerte entre los cuadros por segundo, la latencia del lazo de control y la '
              'distancia de activación; por eso las especificaciones que más pesan son la velocidad de inferencia y la '
              'latencia total, que se midieron en la integración (2.2.5) y fijan el umbral de seguridad del LiDAR '
              '(2.1.10).', AMARILLO)
    for i in (458, 459, 460, 461, 462, 463, 464, 465, 466, 467, 468):
        M.marcar(P[i])

    # ---------------- 2.1.8 LiDAR
    reescribir([470], [
        'En la integración se usó un LiDAR Benewake TF03, que mide hasta 70 m sobre superficies oscuras (Benewake, '
        's. f.), en lugar del TF-Luna considerado en el diseño, cuyo alcance es de unos 8 m. Se conecta a la Jetson Orin '
        'Nano mediante un convertidor USB–TTL y entrega 100 lecturas por segundo; mide la distancia con el tiempo de '
        'ida y vuelta de un pulso infrarrojo, según la ecuación (4).'])
    M.marcar(P[471])
    reescribir([472], [
        'Su función es activar la maniobra con una medida métrica. YOLO dice qué hay al frente y el LiDAR a qué '
        'distancia está. Como es un solo rayo fijo y no siempre incide sobre la persona, la lógica los usa de forma '
        'distinta según el caso: frente a un obstáculo decide el LiDAR con la distancia de seguridad d_safe, y frente a '
        'una persona decide el clasificador de riesgo de 2.2.6, que recibe la lectura del LiDAR como una de sus '
        'entradas. Además, cualquier lectura menor de 3 m mientras el dron avanza detiene el avance sin importar lo que '
        'diga la IA.'])
    M.marcar(P[473])
    reescribir([474], ['La distancia de seguridad sale de la cinemática del frenado y suma tres componentes:'])
    M.texto(P[475], ' v · T_loop, lo que avanza el dron mientras el sistema detecta y ordena frenar.', VERDE)
    M.texto(P[476], ' v² / (2 · a_max), lo que recorre mientras frena con la desaceleración a_max.', VERDE)
    M.texto(P[477], ' d_margen, una distancia fija que cubre los errores de medida y el tamaño del dron.', VERDE)
    M.reemplazar(P[364], 'del proyecto.', 'del proyecto')
    M.marcar(P[374])
    M.claves_extra = getattr(M, 'claves_extra', {})

    def dsafe(v):
        return v * 0.5 + v * v / (2 * 2.5) + 1.5 + 0.4

    filas_ds = [['Avance (m/s)', 'Reacción v·T (m)', 'Frenado v²/2a (m)', 'Margen y radio (m)', 'd_safe (m)',
                 'Holgura mínima al panel en simulación (m)']]
    holg = {1: '1.77 [1.73, 1.82]', 2: '3.14 [3.09, 3.18]', 3: '4.34 [4.29, 4.39]', 4: '5.35 [5.30, 5.40]'}
    for v in (1, 2, 3, 4):
        filas_ds.append([v, f'{v * 0.5:.1f}', f'{v * v / 5:.1f}', '1.9', f'{dsafe(v):.1f}', holg[v]])
    q = M.parrafo(P[479], 'Con los valores del sistema implementado, T_loop = 0.5 s incluye la latencia entre el riesgo y '
                  'la orden (unos 0.1 s en simulación) y el tiempo que tarda el controlador en empezar a frenar; es '
                  'conservador frente a los 9 a 11 ms de inferencia medidos en la Jetson. La aceleración de frenado '
                  'a_max = 2.5 m/s² es la del modo LOITER de ArduPilot con su valor por defecto (LOIT_BRK_ACCEL = 250 '
                  'cm/s²; ArduPilot, s. f.-c) [FALTA: confirmar el valor leyéndolo en la Pixhawk con Mission Planner]. '
                  'El margen es de 1.5 m más 0.4 m de radio del dron (medio brazo del chasis ZD550 más el radio de la '
                  'hélice) [FALTA: fuente o justificación medida del margen de 1.5 m]. Además, se considera riesgo '
                  'cuando faltan menos de 2.5 s para tocar el obstáculo. La {T:dsafe} da d_safe para las velocidades del '
                  'protocolo y la compara con la holgura mínima obtenida en simulación.', AMARILLO)
    cap = M.rotulo(q, 'Tabla', 'dsafe', 'Distancia de seguridad por velocidad de avance')
    tds = M.tabla(cap, filas_ds, [2.2, 2.4, 2.6, 2.6, 1.8, 4.2])
    nds = M.nota(tds, 'Nota. d_safe = v·0.5 + v²/(2·2.5) + 1.5 + 0.4. Holgura en simulación: media e intervalo del 95 % '
                      'de 100 vuelos por velocidad (Anexo F).')
    reescribir([480], [
        'Así, el LiDAR evita que la maniobra se active cuando el obstáculo todavía está lejos y sirve de respaldo cuando '
        'el sol deslumbra la cámara, porque su medida no depende de la imagen.'])
