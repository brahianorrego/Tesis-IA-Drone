"""Preliminares, resumen, introducción, planteamiento, justificación, alcances y limitaciones."""
from motor import AMARILLO, ROJO, TURQ, ROSA, VERDE


def aplicar(M, reescribir):
    P = M.P
    f = lambda t, a=0, b=None: next(p for p in P[a:b] if t in p.text)

    # ---------------- leyenda (solo intervenido; aceptar.py la quita)
    leyenda = [
        'COPIA INTERVENIDA · versión 2 · 13 de octubre de 2026',
        'Colores: ROJO = sobra o está mal; VERDE = reemplaza al rojo que tiene justo antes; AMARILLO = texto nuevo; '
        'TURQUESA = [REVISAR: …] explicación de una corrección; ROSADO = [FALTA: …] algo que hay que agregar. La versión '
        'limpia que acompaña a esta copia ya tiene todo aceptado y solo muestra los [FALTA: …].',
        'Texto: se reescribió completo, párrafo por párrafo, para quitar el tono de texto generado (frases infladas, '
        'muletillas, enumeraciones de tres, conclusiones repetidas) sin cambiar los datos. Los objetivos y la pregunta de '
        'investigación no se tocaron. La metodología conserva su contenido; solo se corrigió la redacción y la figura.',
        'Lo que excede el mínimo acordado (alcances, limitaciones y objetivos) pasó a los anexos, que no cuentan en el '
        'límite de páginas. Cada "Anexo X" del texto es un hipervínculo: Ctrl + clic lleva al anexo.',
        'Al abrir el archivo, Word pregunta si actualiza los campos: responder "Sí" para que se actualicen la tabla de '
        'contenido, las listas de tablas y figuras y la numeración.',
    ]
    for i, t in enumerate(leyenda):
        M.parrafo(P[0], t, AMARILLO, estilo='Normal', bold=(i == 0), antes=True)

    # ---------------- portada y página legal
    M.texto(P[5], ' [FALTA: confirmar si Tania Sierra Galindo sigue como coautora]', ROSA)
    M.texto(P[13], ' [FALTA: título completo del magíster del asesor]', ROSA)
    from docx.oxml.ns import qn
    from docx.text.paragraph import Paragraph
    for x in list(M.body.iter(qn('w:p')))[:200]:
        tx = ''.join(t.text or '' for t in x.iter(qn('w:t')))
        for clave, que in (('Seleccione grupo de investigación', 'el grupo'), ('Seleccione línea de investigación',
                                                                                'la línea')):
            if clave in tx:
                nuevo = M._nuevo_p(x, x.pPr)
                M.texto(Paragraph(nuevo, M.d._body), f'[FALTA: elegir {que} de investigación en la lista desplegable '
                                                     f'de la plantilla]', ROSA, size=10)
    for t in ('Texto de dedicatoria centrado', 'Texto de agradecimientos centrado'):
        p = f(t)
        M.marcar(p)
        M.parrafo(p, '[FALTA: texto (opcional según la plantilla; si no se usa, borrar también el título). Máximo una '
                     'página entre dedicatoria y agradecimientos]', ROSA, ppr_de=p)

    # ---------------- resumen y abstract
    reescribir([149], [
        'Este trabajo presenta la implementación experimental de un sistema que detecta personas y evita obstáculos en '
        'un cuadricóptero operado al aire libre, en un entorno exterior controlado. El sistema combina un detector de '
        'personas preentrenado (YOLO), un sensor LiDAR de proximidad frontal, una computadora de a bordo NVIDIA Jetson '
        'Orin Nano y una controladora de vuelo Pixhawk con ArduPilot. El piloto mantiene el avance en línea recta y el '
        'sistema interviene solo ante una condición de riesgo definida, con una maniobra de detención y ascenso vertical '
        'hasta 3.30 m. La decisión de intervenir la toma un clasificador de riesgo (perceptrón multicapa) entrenado con '
        'datos de simulación etiquetados de forma automática, siempre dentro de reglas de seguridad que tienen '
        'prioridad sobre él. El trabajo se desarrolló en tres fases: selección de la arquitectura por diseño conceptual, '
        'integración en la aeronave con pruebas de activación, comunicación y respuesta, y validación con un protocolo '
        'repetible de escenarios con paneles y personas. En simulación, el protocolo se cumplió en el 100 % de 1300 '
        'vuelos, y la decisión con el clasificador acertó en el 94.0 % de los casos ambiguos frente al 91.2 % de las '
        'reglas solas, con menos detenciones innecesarias. [FALTA: resultados de campo (tasa de éxito con su intervalo '
        'de confianza y latencia medida) y conclusión principal; el resumen completo no debe pasar de 250 palabras]'])
    reescribir([153], [
        'This work presents the experimental implementation of a system that detects people and avoids obstacles on a '
        'quadcopter flown outdoors, in a controlled environment. The system combines a pre-trained person detector '
        '(YOLO), a forward-facing LiDAR proximity sensor, an NVIDIA Jetson Orin Nano onboard computer and a Pixhawk '
        'flight controller running ArduPilot. The pilot keeps flying forward in a straight line and the system acts only '
        'when a defined risk condition appears, with a single maneuver: stop and climb vertically to 3.30 m. The '
        'decision to intervene is made by a risk classifier (multilayer perceptron) trained on automatically labeled '
        'simulation data, always inside safety rules that take precedence over it. The work followed three phases: '
        'architecture selection through conceptual design, integration on the aircraft with activation, communication '
        'and response tests, and validation with a repeatable protocol of scenarios with panels and people. In '
        'simulation, the protocol was met in 100 % of 1300 flights, and the classifier-based decision was right in 94.0 % '
        'of ambiguous cases against 91.2 % for rules alone, with fewer unnecessary stops. [FALTA: field results and main '
        'conclusion; have the final abstract reviewed by a person, not an automatic translator]'])

    # ---------------- introducción
    reescribir(list(range(157, 162)), [
        'Los vehículos aéreos no tripulados se usan cada vez más en tareas civiles y académicas, en parte porque hoy es '
        'posible procesar imágenes a bordo y reaccionar a lo que ve la cámara (Kurunathan et al., 2024). Al aire libre, '
        'sin embargo, volar cerca de personas y obstáculos exige algo más que estabilidad: la aeronave debe percibir el '
        'entorno, decidir si hay riesgo y actuar a tiempo, mientras el viento y la luz del sol afectan a sus sensores '
        '(Merei et al., 2025; Vera-Yanez et al., 2023).',
        'Para detectar personas en tiempo real, los modelos de la familia YOLO son de los más usados, porque localizan '
        'y clasifican los objetos de una imagen en una sola pasada de la red (Redmon et al., 2016). Como vienen '
        'entrenados con conjuntos de datos como COCO, que incluye la clase persona, pueden usarse sin construir un '
        'detector propio (Lin et al., 2014). Eso permite que un trabajo de pregrado dedique su esfuerzo a la integración '
        'del sistema y no al entrenamiento del modelo.',
        'Detectar no basta. Muchos desarrollos muestran que un modelo reconoce personas en un video, pero no llegan a '
        'convertir esa información en una orden que la aeronave ejecute con un retardo aceptable. En las plataformas con '
        'controladora Pixhawk lo habitual es repartir el trabajo: una computadora acompañante procesa la imagen y '
        'decide, y la controladora estabiliza el vuelo y recibe las órdenes por MAVLink (PX4 Autopilot, s. f.).',
        'Este trabajo implementa esa arquitectura en un cuadricóptero del semillero Aerosant. Una cámara frontal y un '
        'LiDAR alimentan a una computadora NVIDIA Jetson Orin Nano, que detecta personas, estima el riesgo y, si hace '
        'falta, ordena a la Pixhawk detenerse y ascender; el piloto conserva el mando en todo momento. El capítulo 1 '
        'plantea el problema y el marco de referencia, el capítulo 2 describe la selección de la arquitectura, su '
        'integración en la aeronave y el protocolo de validación, y el capítulo 3 presenta los resultados.'])

    # ---------------- planteamiento
    reescribir(list(range(163, 169)), [
        'Volar un cuadricóptero al aire libre cerca de personas implica riesgos que la controladora de vuelo no resuelve '
        'por sí sola. La Pixhawk mantiene la aeronave estable, pero no sabe si hay alguien delante. Para evitar una '
        'colisión, el sistema debe ver el obstáculo, interpretar si representa un peligro y responder en pocas décimas de '
        'segundo, todo esto con ráfagas de viento, cambios de iluminación y deslumbramiento solar sobre la cámara (Merei '
        'et al., 2025; Vera-Yanez et al., 2023).',
        'La dificultad no está en detectar a una persona dentro de una imagen, algo que los modelos actuales hacen bien '
        '(Redmon et al., 2016; Lin et al., 2014), sino en convertir esa detección en una acción segura. La latencia del '
        'procesamiento, la oclusión parcial de la persona, el error al estimar su distancia y los límites del hardware '
        'embarcado pueden hacer que una detección correcta llegue tarde o produzca una orden equivocada (Choutri et al., '
        '2024).',
        'En los trabajos de pregrado este problema suele quedar a medias: se demuestra que el modelo detecta, pero la '
        'cadena completa entre la cámara, la decisión y la controladora no se prueba en una aeronave real (Merei et al., '
        '2025). Este trabajo aborda esa cadena con recursos accesibles: una cámara frontal, un LiDAR de proximidad, una '
        'computadora NVIDIA Jetson Orin Nano y una controladora Pixhawk. La respuesta se limita a detener el avance y '
        'ascender; no se busca una navegación autónoma completa.',
        'El problema central es, entonces, cómo integrar un sistema de detección de personas y evasión básica de '
        'obstáculos en un cuadricóptero mediante inteligencia artificial preentrenada, de modo que la información de la '
        'cámara frontal y del LiDAR se convierta en decisiones automáticas de seguridad, articulando percepción, decisión '
        'y control de vuelo en un entorno exterior controlado.'])

    # ---------------- justificación
    reescribir(list(range(170, 177)), [
        'El trabajo atiende un problema real de la operación de aeronaves no tripuladas: mantener la seguridad cuando la '
        'aeronave vuela cerca de personas y obstáculos. Su valor técnico está en la integración. La cámara, la '
        'computadora de a bordo, el LiDAR y la controladora deben funcionar como un solo sistema, y eso obliga a medir '
        'latencias, a definir prioridades entre el piloto y la lógica automática y a comprobar en la aeronave que una '
        'orden de seguridad se ejecuta (Vera-Yanez et al., 2023).',
        'La elección tecnológica hace viable el trabajo dentro de un pregrado. Un detector YOLO preentrenado en COCO '
        'evita construir una base de datos y entrenar un modelo desde cero (Redmon et al., 2016; Lin et al., 2014). La '
        'separación entre una computadora acompañante, que procesa y decide, y una controladora Pixhawk, que estabiliza, '
        'es la arquitectura habitual en sistemas UAV y permite registrar datos y evaluar cada módulo por separado (PX4 '
        'Autopilot, s. f.). El LiDAR aporta una medida directa de distancia que no depende de la iluminación, útil cuando '
        'el sol deslumbra la cámara (Liang et al., 2023; Gerencheal & Lee, 2025).',
        'Para la formación en Ingeniería Aeronáutica, el trabajo reúne en un mismo problema el control de vuelo, la '
        'instrumentación, la integración de sistemas y la seguridad operacional, y muestra cómo una decisión tomada por '
        'un programa cambia el comportamiento de la aeronave.',
        'La propuesta, además, es alcanzable y medible. No pretende resolver la navegación autónoma, sino demostrar en '
        'exteriores, con un protocolo repetible, que la arquitectura reacciona ante personas y obstrucciones en una '
        'trayectoria de avance frontal. Sus resultados pueden servir de base a trabajos posteriores sobre percepción y '
        'control de cuadricópteros.'])

    # ---------------- objetivos y problema: sin cambios
    M.parrafo(P[179], '[REVISAR: objetivos, objetivos específicos y pregunta de investigación se dejan exactamente como '
                      'los aprobó el comité]', TURQ, estilo='Párr.APA')

    # ---------------- alcances (texto de la carta, con Jetson)
    A = P[188:198]
    M.reemplazar(A[0], 'la Raspberry Pi', 'la computadora de a bordo (NVIDIA Jetson Orin Nano)')
    M.reemplazar(A[1], 'la Raspberry Pi,', 'la computadora de a bordo NVIDIA Jetson Orin Nano,')
    reescribir([188 + 3], [
        'Se implementará en la computadora de a bordo (NVIDIA Jetson Orin Nano) el módulo de percepción–decisión, '
        'integrando el detector de personas con una lógica de evasión básica basada en reglas y estados, dentro de la '
        'cual un clasificador de riesgo (perceptrón multicapa) decide cuándo intervenir; las reglas de seguridad '
        'conservan siempre la prioridad.'])
    M.reemplazar(A[4], 'respuesta,', 'respuesta.')
    M.reemplazar(A[6], 'la Raspberry Pi y la Pixhawk', 'la Jetson Orin Nano y la Pixhawk')
    M.reemplazar(A[8], 'frente a obstáculos fijos ubicados en la trayectoria de avance',
                 'frente a obstáculos fijos y a personas (primero con un maniquí) ubicados en la trayectoria de avance o '
                 'cerca de ella')
    M.parrafo(A[9], '[REVISAR: alcances con el texto de la carta al comité; solo se cambió Raspberry Pi por Jetson Orin '
                    'Nano, se ajustó el alcance del módulo de decisión y se incluyó a las personas en el protocolo, como '
                    'pide el objetivo general]', TURQ, estilo='Párr.APA')

    # ---------------- limitaciones
    L = P[199:209]
    reescribir([199], [
        'El detector de personas no se entrenará desde cero: se usará un modelo YOLO preentrenado en COCO, por lo que su '
        'desempeño dependerá de la cobertura y de las características de ese conjunto de datos. El único componente que '
        'se entrena dentro del proyecto es el clasificador de decisión, una red pequeña (perceptrón multicapa de 15 '
        'entradas) que no procesa imágenes y se entrena con datos de simulación etiquetados de forma automática.'])
    reescribir([201], [
        'Como criterio de delimitación, la arquitectura se basa en la cámara frontal, el sensor LiDAR de proximidad '
        'frontal, la computadora de a bordo NVIDIA Jetson Orin Nano y la controladora Pixhawk. Los elementos propios de '
        'la plataforma de vuelo, como el receptor GPS de la controladora (que el modo GUIDED exige en exteriores) y el '
        'estabilizador de cámara de dos ejes con inclinación fija, no aportan entradas nuevas a la lógica de decisión. '
        'No se integrarán sensores adicionales de percepción, como otros LiDAR, radares o cámaras de profundidad.'])
    reescribir([203], [
        'La validación en campo se hará con un número limitado de repeticiones por escenario (diez), por lo que la tasa '
        'de éxito de campo se reportará con su intervalo de confianza y se complementará con la evaluación del mismo '
        'protocolo en simulación.'])
    reescribir([204], [
        'Además del avance frontal, se evaluará un modo estático en el que el dron se mantiene en vuelo estacionario y no '
        'se desplaza por sí mismo; en ese modo la única respuesta posible es el ascenso vertical cuando una persona se '
        'aproxima. No se contemplan desplazamientos horizontales autónomos.'])
    M.reemplazar(L[9], 'tendrá prioridad sobre el comando manual de avance frontal.',
                 'tendrá prioridad sobre el comando manual de avance frontal, pero no sobre la parada de emergencia ni '
                 'sobre el cambio de modo que hace el piloto con el radiocontrol.')
    M.parrafo(L[9], '[REVISAR: se corrigieron cuatro limitaciones que contradecían a los alcances o a los objetivos '
                    '("dron fijo sin evasión", "no es validación por repeticiones", "sin sensores adicionales" y "sin '
                    'entrenamiento desde cero"). Antes de entregar, preguntar al asesor si el comité debe conocer el cambio '
                    'de Raspberry Pi a Jetson Orin Nano]', TURQ, estilo='Párr.APA')
