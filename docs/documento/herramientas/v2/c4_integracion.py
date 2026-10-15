"""Capítulo 2 · 2.2 integración, 2.3 protocolo; capítulos 3 a 5."""
import copy
import os
from docx.oxml.ns import qn
from docx.text.run import Run

from motor import AMARILLO, ROJO, TURQ, ROSA, VERDE


def aplicar(M, reescribir, mover, DIAG):
    P, T = M.P, M.T
    FOTOS = os.environ.get('FOTOS', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fotos'))
    from c3_arquitectura import celda
    for i, k in ((488, ('Figura', 'dron')), (493, ('Figura', 'conex')), (501, ('Tabla', 'aeronav')),
                 (506, ('Figura', 'mp')), (520, ('Figura', 'detector')), (548, ('Tabla', 'estaticas')),
                 (552, ('Figura', 'capturas'))):
        M.claves[P[i]._p] = k

    # ---------------- 2.2 intro y 2.2.1
    reescribir([482], [
        'Para el segundo objetivo, el concepto de la {T:implementado} se llevó a la aeronave y se comprobó su '
        'funcionamiento en tierra, sin vuelos. La metodología (1.9.2.2) planteaba implementar la percepción, la decisión y '
        'la comunicación y verificarlas con pruebas de activación, comunicación y respuesta. Antes hubo que resolver un '
        'paso que no estaba previsto: el cuadricóptero del semillero Aerosant se recibió desarmado, así que la '
        'integración empezó por construir la plataforma. Este apartado sigue el orden en que se trabajó: ensamble, '
        'conexiones, verificación en Mission Planner, validación del detector, despliegue en la computadora de a bordo, '
        'lógica de decisión y pruebas estáticas.'])
    reescribir([486], [
        'La energía la suministra una batería LiPo 4S de 6200 mAh (14.8 V nominales y 77 Wh). Entre la batería y la '
        'placa de distribución se intercaló el Power Module, que alimenta la Pixhawk y mide la tensión y la corriente del '
        'paquete; esas lecturas son las que usa el failsafe de batería de 2.2.3. La carga útil la completan la '
        'computadora de a bordo, una NVIDIA Jetson Orin Nano, y el conjunto de cámara y LiDAR, montado sobre un '
        'estabilizador BaseCam en la parte frontal para que ambos sensores apunten en la misma dirección. Las hélices se '
        'montaron según el sentido de giro que ArduCopter asigna a cada motor en configuración X: motores 1 y 2 en '
        'sentido antihorario y 3 y 4 en sentido horario.'])
    reescribir([487], ['La {F:dron} muestra la aeronave ensamblada; las fotografías del armado por etapas están en el Anexo C.'])
    M.marcar(P[490])
    from datos_tablas import INVENTARIO
    q = M.parrafo(P[490], 'La {T:inventario} lista los componentes del cuadricóptero integrado, con su referencia, su cantidad y '
                          'la función que cumple cada uno.', AMARILLO)
    cap = M.rotulo(q, 'Tabla', 'inventario', 'Componentes del cuadricóptero integrado')
    t = M.tabla(cap, INVENTARIO, [3.4, 5.6, 1.6, 4.9])
    q = M.parrafo(t, 'La masa del cuadricóptero se midió con una báscula de cocina SF-400 (capacidad de 10 kg y resolución '
                     'de 1 g) y dio 2371 g ({F:masa}). [FALTA: aclarar qué incluye esa medición (batería, Jetson, cámara y '
                     'estabilizador), la fecha y la masa de cada subsistema; con ella se calcula la relación '
                     'empuje–peso]', AMARILLO)
    cap = M.rotulo(q, 'Figura', 'masa', 'Medición de la masa del cuadricóptero')
    fig = M.figura(cap, os.path.join(FOTOS, 'masa_bascula.jpg'), ancho_cm=15.5, color=AMARILLO)
    q = M.nota(fig, 'Nota. A la izquierda, el cuadricóptero sobre la báscula; a la derecha, la lectura: 2371 g. [REVISAR: '
                    'confirmar la lectura y la configuración medida]')
    q = M.parrafo(q, 'El modo GUIDED exige posición GPS, por eso el cuadricóptero lleva un módulo GPS sobre el chasis '
                     '({F:gps}). [FALTA: modelo del módulo GPS]', AMARILLO)
    cap = M.rotulo(q, 'Figura', 'gps', 'Módulo GPS montado sobre el chasis')
    fig = M.figura(cap, os.path.join(FOTOS, 'gps.jpg'), ancho_cm=7.5, color=AMARILLO)
    M.nota(fig, 'Nota. Vista superior del módulo GPS con su cable hacia la Pixhawk.')

    # ---------------- 2.2.2
    reescribir([492], [
        'La {F:conex} separa los caminos de energía (líneas gruesas) y de datos (líneas delgadas). La energía sale de la '
        'batería, pasa por el Power Module y llega a la placa de distribución, que alimenta los cuatro variadores; de la '
        'misma placa sale un convertidor buck que entrega 12 V a la Jetson. La Pixhawk se alimenta desde el Power Module '
        'y no comparte línea con la computadora. Esta separación responde al requerimiento RF-07: la Jetson consume '
        'bastante más que la controladora, y el convertidor estabiliza su tensión frente a las caídas que producen los '
        'motores al acelerar.'])
    M.marcar(P[495])
    M.figura(P[495], f'{DIAG}/09_conexiones.png', color=VERDE)
    M.marcar(P[496])
    M.parrafo(P[496], '[REVISAR: el esquema original (hecho con Gemini) no mostraba la salida AUX1 hacia el '
                      'estabilizador, el GPS ni la cámara USB; se redibujó con las conexiones reales]', TURQ)
    reescribir([497], [
        'En los datos, el control manual sigue la cadena habitual de ArduCopter: el radiocontrol Futaba T14SG transmite '
        'al receptor Corona, un codificador PPM agrupa los canales y la Pixhawk los lee por su entrada RC. El enlace '
        'entre la controladora y la Jetson es serie: el puerto TELEM2 de la Pixhawk va a la UART del conector de 40 pines '
        'de la Jetson (pin 8 TX, pin 10 RX y pin 6 GND, con TX y RX cruzados), a 115200 baudios y con MAVLink 2. A 460800 '
        'y 921600 baudios la Pixhawk no interpretaba lo que transmitía la Jetson, por la imprecisión del reloj de su '
        'UART. El cable de 5 V del puerto se dejó sin conectar para que las placas no se alimenten entre sí.',
        'El LiDAR se conecta por un adaptador USB–TTL, y la cámara y el estabilizador por USB; como Linux puede cambiar '
        'los nombres de los puertos al reiniciar, el programa los abre por sus rutas fijas en /dev/serial/by-id/. La '
        'inclinación del estabilizador se ordena con una señal PWM desde la salida AUX1 de la Pixhawk (comando '
        'DO_SET_SERVO), con pwm = 1500 + θ·500/45 µs, porque el firmware 2.2 de la BaseCam no obedece órdenes por el '
        'puerto serie. En las pruebas se deja fija en −5°.'])

    # ---------------- 2.2.3
    reescribir([500], [
        'El procedimiento siguió la configuración inicial de ArduCopter: carga del firmware y selección del marco Quad '
        'X, calibración del acelerómetro, de la brújula y del radiocontrol, asignación de los modos de vuelo al '
        'interruptor, configuración de los failsafes y prueba individual de los motores para confirmar su numeración y '
        'sentido de giro. La {T:aeronav} resume cada verificación y su criterio de aceptación. [FALTA: confirmar los '
        'modos finales del interruptor CH5 y el uso de CH7 como interruptor del modo experimental]'])
    for fila, texto in {1: 'Cumple: ArduCopter 4.7.0 reconocido por Mission Planner',
                        4: 'Cumple: cuatro ejes e interruptor leídos sin cruces',
                        5: 'Cumple: cambio de modo reflejado en Mission Planner',
                        8: 'Cumple: respuesta simétrica de los cuatro motores'}.items():
        celda(M, T[14], fila, 3, texto)
    M.marcar(P[502])
    reescribir([505], [
        'La {F:mp} muestra la pantalla de vuelo de Mission Planner con la aeronave en tierra: el horizonte artificial '
        'responde a la inclinación del chasis, el modo y el estado de armado se actualizan y no aparecen mensajes de '
        'prearmado, lo que indica que la controladora lee sus sensores y atiende al radiocontrol.'])
    M.marcar(P[508])
    from datos_tablas import PARAM_ARDUPILOT, MODULOS
    q = M.parrafo(P[508], 'Los parámetros de ArduPilot que se cambiaron en esta etapa y en la integración con la Jetson están en '
                          'la {T:ardupilot}, cada uno con su motivo.', AMARILLO)
    cap = M.rotulo(q, 'Tabla', 'ardupilot', 'Parámetros de ArduPilot cambiados o relevantes')
    t = M.tabla(cap, PARAM_ARDUPILOT, [4.8, 4.2, 6.5])
    M.nota(t, 'Nota. Los valores de LOIT_BRK_ACCEL y GUID_TIMEOUT se leen en la Pixhawk con Mission Planner.')

    # ---------------- 2.2.4
    reescribir([509], ['2.2.4 Primera versión del algoritmo de detección'])
    reescribir([510], [
        'La primera versión del detector (yolo_tracking.py) se escribió en Python y se ejecutó en la Jetson con Ubuntu '
        '24.04. Usa Ultralytics para la inferencia y el seguimiento, OpenCV para la captura y la visualización, y los '
        'módulos time, csv y os para el registro de eventos.'])
    reescribir([512], [
        'El modelo es un YOLO ligero preentrenado con COCO. Aunque reconoce 80 clases, el programa filtra solo la clase '
        'person. Para aumentar los cuadros por segundo, el modelo se convirtió al motor de inferencia TensorRT.'])
    reescribir([514], [
        'El seguimiento usa model.track(frame, persist=True), que asigna a cada persona un identificador y lo mantiene '
        'entre cuadros aunque se mueva por la imagen.'])
    reescribir([516], [
        'Esta primera versión solo monitorea y advierte: clasifica la cercanía y la posición de la persona, pero no envía '
        'órdenes a la Pixhawk. La decisión de intervenir y el envío de comandos están en el módulo de 2.2.6. Su diagrama '
        'de flujo se muestra en la {F:flujo}.'])
    reescribir([518], [
        'Antes de instalarlo en la aeronave, el detector se probó en un computador portátil con su cámara integrada y luz '
        'artificial ({F:detector}). Así se descartaron errores de lógica y de configuración sin las restricciones de '
        'energía del sistema embebido.'])
    reescribir([522], [
        'Nota. La persona que aparece autorizó el uso de su imagen con fines académicos. [FALTA: reemplazar por una '
        'captura del detector YOLO de personas (la ventana actual dice "Detección de Rostros") y confirmar por escrito la '
        'autorización de la persona]'])
    for i in (523, 524, 525, 526, 527, 528):
        M.marcar(P[i])
    cap = M.rotulo(P[528], 'Figura', 'flujo', 'Diagrama de flujo del algoritmo de detección de personas')
    M.figura(cap, f'{DIAG}/11_deteccion.png', alto_max=18.0, color=VERDE)
    M.parrafo(P[528], '[REVISAR: el diagrama original se redibujó con el mismo estilo del resto de figuras y con los '
                      'pasos que describe el texto: carga del modelo, lectura del cuadro, persona de mayor área, zona, '
                      'persistencia del riesgo y registro en el archivo CSV]', TURQ)

    # ---------------- 2.2.5
    reescribir([531], [
        'El entorno de ejecución es Ubuntu 24.04 (L4T R39.2.1, JetPack 7) con Python 3.12 y un entorno virtual creado con '
        'la opción --system-site-packages, que permite usar dentro del entorno las bibliotecas de JetPack (TensorRT y '
        'CUDA). No se usó ROS 2 ni Nav2: con un LiDAR de un solo rayo no hay un mapa que construir, y el sistema se '
        'resolvió con programas en Python que se comunican directamente por MAVLink.'])
    reescribir([532], [
        'La cámara CSI IMX219 mostraba pantallas verdes y a veces bloqueaba el servicio nvargus-daemon, que administra las '
        'cámaras CSI; había que reiniciarlo para recuperar la imagen. Esa inestabilidad no es aceptable en un sistema de '
        'seguridad, así que se cambió por una cámara web USB (Sonix, 640×480, campo de visión horizontal medido de 38.9°) '
        'montada sobre el estabilizador BaseCam. La programación se hizo desde un portátil por SSH con Visual Studio '
        'Code, igual que en vuelo, donde la Jetson opera sin monitor. El modelo YOLO26n se exportó a TensorRT en media '
        'precisión (FP16): cada cuadro tarda entre 9 y 11 ms, frente a los 33 ms que separan dos cuadros de la cámara.'])
    reescribir([533], [
        'La {F:jetson} muestra la primera ejecución del programa de control en la Jetson. La interfaz y la detección '
        'funcionan, y el sistema reconoce que faltan el LiDAR y el estabilizador (paneo --) y se bloquea por seguridad '
        '(FALLA). Esto confirma que las dependencias de Python y de visión quedaron instaladas antes de conectar el resto '
        'del hardware.'])
    M.marcar(P[534])
    M.marcar(P[535])
    M.rotulo(P[535], 'Figura', 'jetson', 'Validación del despliegue de software en la Jetson Orin Nano', color=VERDE)

    # ---------------- 2.2.6
    reescribir([537], ['2.2.6 Arquitectura de software y lógica de decisión'])
    q = reescribir([538], [
        'El código se organiza en módulos, uno por archivo, que resume la {T:modulos}; los listados principales están en '
        'el Anexo E. En el cuerpo del documento solo se presentan la arquitectura ({F:arq}) y los estados de la maniobra '
        '({F:estados}).'])
    cap = M.rotulo(q, 'Tabla', 'modulos', 'Módulos del software de a bordo y de simulación')
    t = M.tabla(cap, MODULOS, [6.4, 9.1])
    for i in (539, 540, 541):
        M.marcar(P[i])
    cap = M.rotulo(P[541], 'Figura', 'arq', 'Arquitectura de percepción, decisión y control')
    fig = M.figura(cap, f'{DIAG}/01_arquitectura.png', alto_max=19.0)
    reescribir([542], [
        'La cámara alimenta a la IA 1, el detector YOLO26n con seguimiento. El estabilizador no sigue a la persona: '
        'mantiene la cámara y el LiDAR con una inclinación fija de −5°, de modo que el LiDAR mide lo que hay al frente, '
        'en la trayectoria. De cada cuadro se calculan quince entradas para la IA 2: de la caja de YOLO, el alto, el '
        'ancho, el área, el ángulo horizontal y su variación, la confianza y el número de cuadros seguidos con detección; '
        'del LiDAR, la distancia y si la lectura es utilizable; de la Pixhawk, la velocidad que estima su filtro EKF; y '
        'de un seguimiento alfa-beta de la persona, la distancia, la velocidad de acercamiento, la velocidad lateral y el '
        'tiempo sin detección. Las entradas se calculan con la misma función en la simulación y en el dron, para que el '
        'modelo reciba en vuelo lo mismo que vio al entrenarse.'])
    q = reescribir([543], [
        'La IA 2 es un perceptrón multicapa de scikit-learn con dos capas ocultas de 32 y 16 neuronas (ReLU) y una sola '
        'salida: la probabilidad de que, si el piloto mantiene su mando, en los próximos 3 s ocurra un choque o una '
        'persona quede a menos de 2 m del dron. Si esa probabilidad supera 0.7 durante 2 cuadros seguidos, el sistema '
        'pasa de CONTINUAR a DETENER_Y_ASCENDER. No hay salidas de evasión lateral, lo que respeta la limitación de '
        '1.4.2. El modelo se entrenó con 2 551 725 cuadros de vuelos simulados (13 % con riesgo), etiquetados '
        'automáticamente con la verdad del simulador, y se probó con 533 085 cuadros de mundos que no participaron en '
        'el entrenamiento: área bajo la curva ROC de 0.974 y 0.3 % de falsos positivos por cuadro. El umbral y el número '
        'de cuadros se eligieron con mundos de validación, nunca con el protocolo. La {T:clasif} reúne los datos y el '
        'desempeño por cuadro; los detalles del entrenamiento están en el Anexo F. [FALTA: validar el clasificador con '
        'datos reales del dron (pasos 4 y 5 del plan de pruebas) y reportar el resultado]'])
    from datos_tablas import CLASIFICADOR, CONFUSION
    cap = M.rotulo(q, 'Tabla', 'clasif', 'Datos y desempeño del clasificador por cuadro')
    t = M.tabla(cap, CLASIFICADOR, [7.0, 8.0])
    q = M.nota(t, 'Nota. La exhaustividad por cuadro no mide la seguridad: un riesgo dura muchos cuadros y basta detectarlo '
                  'en dos seguidos; la seguridad se mide en lazo cerrado.')
    q = M.parrafo(q, 'De los 533 085 cuadros de prueba, 61 335 tenían riesgo real y el clasificador marcó 45 619 (74.4 %); '
                     'de los 471 750 sin riesgo, solo 1 420 dieron una alarma falsa (0.3 %). La {T:confusion} muestra la '
                     'matriz completa.', AMARILLO)
    cap = M.rotulo(q, 'Tabla', 'confusion', 'Matriz de confusión en la prueba (por cuadro)')
    t = M.tabla(cap, CONFUSION, [5.0, 5.0, 5.0])
    q = M.parrafo(t, 'Las curvas de la {F:roc} resumen el desempeño: el área bajo la curva ROC es de 0.974 y la precisión '
                     'media, de 0.914.', AMARILLO)
    cap = M.rotulo(q, 'Figura', 'roc', 'Curvas ROC y de precisión-exhaustividad del clasificador')
    M.figura(cap, f'{M.repo}/simulacion/informes/minimo_tesis_decisor_curvas.png', ancho_cm=15.5, color=AMARILLO)
    q = reescribir([544], [
        'La salida del clasificador opera dentro de una envolvente de reglas que no puede saltar: (1) si el LiDAR mide '
        'menos de 3 m mientras el dron avanza, se detiene el avance sin importar lo que diga la IA; (2) el ascenso por '
        'una persona solo lo autoriza el árbitro de seguridad, cuando la persona está a menos de 3 m, o a menos de 8 m y '
        'acercándose; antes de eso la IA solo puede detener; (3) una salvaguarda geométrica detiene el dron si una '
        'persona seguida va a pasar a menos de 2 m en menos de 1.5 s; y (4) la parada de emergencia del radiocontrol '
        '(CH8) y el cambio de modo del piloto mandan siempre. El programa nunca arma ni despega por sí mismo y, si falta '
        'la cámara, el detector o el LiDAR, detiene el avance (RF-11). La {F:estados} muestra los estados de la '
        'maniobra.'])
    cap = M.rotulo(q, 'Figura', 'estados', 'Estados de la intervención')
    fig = M.figura(cap, f'{DIAG}/02_estados.png', alto_max=18.0)
    M.nota(fig, 'Nota. CH5: modo de vuelo; CH7: interruptor del modo experimental; CH8: parada de emergencia.')
    reescribir([545], [
        'La orden llega a la Pixhawk por MAVLink en el modo GUIDED, que exige posición GPS con fijación 3D (ArduPilot, '
        's. f.-b). En la secuencia prevista, el piloto despega y vuela en LOITER a 2.3 m, activa el modo experimental '
        'con un interruptor del radiocontrol y avanza. Solo cuando el sistema decide intervenir, la Jetson cambia la '
        'Pixhawk a GUIDED, anula la velocidad horizontal y ordena subir hasta 3.30 m con una consigna de posición, que '
        'GUIDED sostiene por sí mismo. El piloto retoma el mando moviendo el interruptor de modos; si la Jetson deja de '
        'enviar consignas, el parámetro GUID_TIMEOUT hace que la Pixhawk frene sola. Cada ejecución escribe un registro '
        'CSV con el modo, el armado, la altura, el voltaje, el estado de la decisión, la distancia y su fuente, la '
        'probabilidad, las órdenes enviadas y las latencias (RF-09). Los parámetros de ArduPilot están en la {T:ardupilot} y '
        'los del software, en el Anexo D.'])

    # ---------------- 2.2.7
    reescribir([547], [
        'Las pruebas estáticas se hicieron con el cuadricóptero completo fijo en tierra y la Jetson alimentada desde la '
        'placa de distribución a través del convertidor, igual que en vuelo. Corresponden al modo estático de 1.4.2: la '
        'aeronave no se mueve y las que se mueven son las personas. Se organizaron según las tres condiciones del '
        'objetivo ({T:estaticas}): activación, comunicación y respuesta.'])
    t14 = T[15]
    for fila, texto in {3: 'Verificada: 100 lecturas por segundo por USB-TTL (6 de octubre de 2026)',
                        4: 'Verificada por USB; el control por UART se descartó y la inclinación va por PWM desde AUX1',
                        5: 'Verificada: 115200 baudios, 10 de 10 comandos con confirmación (ACK)',
                        7: '[FALTA: resultado en banco (paso 5 del plan de pruebas)]',
                        8: '[FALTA: resultado en banco (paso 3 del plan de pruebas)]'}.items():
        c = t14.cell(fila, 3)
        rp = None
        for r in c._tc.iter(qn('w:r')):
            if rp is None and r.find(qn('w:rPr')) is not None:
                rp = copy.deepcopy(r.find(qn('w:rPr')))
                for h in rp.findall(qn('w:highlight')):
                    rp.remove(h)
            Run(r, None).font.highlight_color = ROJO
        M.texto(c.paragraphs[0], ' ' + texto, VERDE, rpr=rp)
    M.marcar(P[549])
    reescribir([550], [
        'En la prueba de respuesta, una o varias personas caminaron frente a la aeronave acercándose, alejándose y '
        'desplazándose de lado, mientras el sistema, ejecutado desde el portátil por SSH, dibujaba el recuadro sobre '
        'cada una y le asignaba la zona izquierda, centro o derecha. Como el área del recuadro crece aproximadamente con '
        'el inverso del cuadrado de la distancia, el tamaño de la caja sirve para estimar la cercanía cuando el láser no '
        'toca a la persona.'])
    reescribir([551], ['La {F:capturas} reúne capturas de la prueba con la persona a la izquierda, al centro y a la '
                       'derecha del encuadre.'])
    M.texto(P[553], '[FALTA: insertar las tres capturas del dron completo detectando a la persona a la izquierda, al '
                    'centro y a la derecha]', ROSA)
    reescribir([554], ['Nota. Capturas del sistema en ejecución en la Jetson.'])

    # ---------------- 2.2.8
    reescribir([556], [
        'La verificación de 2.2.7 y las pruebas de banco posteriores cubren la percepción y la comunicación: la aeronave '
        'integrada detecta personas con su propia alimentación, el LiDAR entrega 100 lecturas por segundo y el enlace '
        'MAVLink responde. Antes de volar quedan cinco comprobaciones: que la BaseCam, alimentada, lea el pulso de AUX1; '
        'el cambio a GUIDED y la retoma del piloto en banco, midiendo la latencia entre el riesgo y la orden (criterio: '
        'menos de 150 ms); la grabación de datos reales con el dron sin hélices sobre un vehículo ({F:campofoto}, 2.3.5), para comparar '
        'los sensores con su modelo de simulación; el clasificador en modo sombra, que decide y registra pero no manda; y la '
        'fijación GPS 3D que exige GUIDED. [FALTA: resultado de estas cinco comprobaciones]'])
    q = reescribir([557], [
        'Las pruebas siguientes van de menor a mayor riesgo: ejecución en banco sin la Pixhawk, que muestra qué '
        'decidiría el sistema sin enviar nada; ejecución en banco con la Pixhawk conectada y sin hélices, para comprobar '
        'el cambio de modo y la retoma del piloto; y simulación del lazo MAVLink en el simulador SITL de ArduPilot. Solo '
        'después se pasa al vuelo exterior, con observador y piloto de seguridad, según el protocolo de 2.3 y la lista de '
        'verificación de 2.3.5.'])

    # =================================================================== 2.3 protocolo
    filas_v = [
        ['Valor', 'Dónde se usa', 'Por qué ese valor'],
        ['2.3 m', 'Altura de vuelo del piloto', 'Con la cámara y el LiDAR a −5°, el rayo toca el suelo a unos 26 m '
         '(2.3 / tan 5°), que es el alcance útil del LiDAR; un panel de 2.6 m queda dentro del rayo.'],
        ['3.30 m', 'Altura a la que sube el dron', 'Una persona alcanza al dron si está a menos de 1.0 m en horizontal y '
         'por debajo de 2.6 m (persona alta con el brazo extendido y un salto). Se suman 0.7 m que cubren el radio del '
         'dron y el error de altura. En simulación el dron sale de ese alcance 0.40 s después de la orden. [FALTA: fuente '
         'antropométrica del alcance de pie y del salto vertical]'],
        ['1.72 m', 'Estatura que supone la Jetson para estimar la distancia', 'Supera el promedio de los hombres '
         'colombianos nacidos entre 1980 y 1984, 170.6 cm (Meisel Roca & Vega Argote, 2007); es conservadora para el '
         'alcance.'],
        ['2 m', 'Zona de riesgo de una persona', 'Brazo extendido (1.0 m), radio del dron (0.4 m) y 0.6 m de margen.'],
        ['3 m', 'Bloqueo frontal y persona "en amenaza"', 'Es d_safe a unos 1.4 m/s ({T:dsafe}): por debajo de 3 m el '
         'dron ya no frena con margen a velocidad de maniobra, así que la orden es fija.'],
        ['8 m', 'El árbitro autoriza subir si la persona se acerca', 'Una persona que corre (3.3 m/s) tarda (8 − 2) / '
         '3.3 = 1.8 s en llegar a 2 m; el sistema necesita unos 0.5 s (0.1 s para decidir y 0.4 s para salir del '
         'alcance).'],
        ['4 m/s', 'Velocidad máxima del piloto (LOIT_SPEED)', 'Mayor velocidad a la que las reglas detienen el dron con '
         'margen frente a una persona quieta en al menos el 95 % de los vuelos simulados.'],
        ['3 s', 'Horizonte de predicción del clasificador', 'Cubre la reacción (0.5 s) y el frenado desde 4 m/s (0.8 s y '
         '3.2 m) con margen.'],
        ['0.7 y 2 cuadros', 'Umbral y persistencia del clasificador', 'Se eligieron con mundos de validación: el mínimo '
         'de activaciones innecesarias sin dejar pasar más riesgos que las reglas.'],
        ['150 ms', 'Latencia máxima aceptada entre riesgo y orden', 'La simulación supone 100 ms y sigue sin choques '
         'hasta 300 ms a las velocidades del protocolo.'],
        ['10 repeticiones', 'Repeticiones de campo por escenario', 'Diez éxitos de diez dan un intervalo de Wilson del '
         '95 % de 72 % a 100 %: muestran que el sistema funciona y validan latencia y frenado.'],
    ]
    q = M.parrafo(q, 'La {T:traza} relaciona cada requerimiento funcional con la prueba que lo verifica y con su estado actual.',
                  AMARILLO)
    filas_traza = [
        ['Requerimiento', 'Cómo se verifica', 'Evidencia', 'Estado'],
        ['RF-01 Captura visual', 'Video continuo de la cámara USB a 640×480 y 30 cuadros/s', 'Despliegue en la Jetson (2.2.5)', 'Verificado'],
        ['RF-02 Detección de personas', 'Detector YOLO26n con TensorRT sobre personas en movimiento', '9 a 11 ms por cuadro; prueba de respuesta (2.2.7)', 'Verificado'],
        ['RF-03 Telemetría de proximidad', 'Lectura del LiDAR TF03 por USB-TTL', '100 lecturas por segundo (2.2.7)', 'Verificado'],
        ['RF-04 Procesamiento a bordo', 'Inferencia y decisión en la Jetson Orin Nano', 'Ejecución sin enlace de video a tierra (2.2.5)', 'Verificado'],
        ['RF-05 Enlace MAVLink', 'Comandos de la Jetson a la Pixhawk por TELEM2', '115200 baudios; 10 de 10 comandos con confirmación', 'Verificado'],
        ['RF-06 Maniobra de evasión', 'Cambio a GUIDED, ascenso a 3.30 m y retoma del piloto en banco', '[FALTA: resultado del paso 3 del plan de pruebas]', 'Pendiente'],
        ['RF-07 Gestión de potencia', 'Arranque de la Jetson con la alimentación de a bordo', 'Sin reinicios espontáneos (2.2.7)', 'Verificado'],
        ['RF-08 Tolerancia a perturbaciones', 'Condiciones con viento, luz y sensores degradados', 'Simulación (3.3); campo [FALTA: ensayos]', 'Parcial'],
        ['RF-09 Trazabilidad de eventos', 'Registro CSV de modo, distancia, decisión y latencias', 'Registro de la Jetson (2.2.6) [FALTA: ejemplo de registro real]', 'Parcial'],
        ['RF-10 Delimitación de la respuesta', 'Salidas del clasificador: solo detener y ascender', 'Lógica de 2.2.6; sin evasión lateral', 'Verificado'],
        ['RF-11 Protocolo de fallo seguro', 'Bloqueo ante falta de cámara, detector o LiDAR; GUID_TIMEOUT', '[FALTA: prueba en banco]', 'Pendiente'],
    ]
    cap = M.rotulo(q, 'Tabla', 'traza', 'Verificación de los requerimientos funcionales')
    t = M.tabla(cap, filas_traza, [3.8, 5.0, 4.8, 1.9])
    q = M.nota(t, 'Nota. "Verificado" significa que la prueba se hizo con la aeronave en tierra; "Parcial", que solo está '
                  'la parte de simulación; "Pendiente", que falta el resultado. [REVISAR: confirmar cada estado con la '
                  'bitácora de pruebas]')
    q = M.parrafo(q, '2.3 Protocolo de validación experimental', AMARILLO, ppr_de=P[481])
    q = M.parrafo(q, 'Para el tercer objetivo se definió un protocolo con los mismos escenarios en simulación y en '
                     'campo. La simulación sirvió para fijar los parámetros iniciales de operación y los criterios de '
                     'seguridad, como prevé el alcance de 1.4.1, antes de arriesgar la aeronave; los vuelos de campo '
                     'validan el sistema real. El modelo de simulación está en el Anexo F.')
    q = M.parrafo(q, '2.3.1 Escenarios y criterios de éxito', AMARILLO, ppr_de=P[484])
    q = M.parrafo(q, 'El piloto avanza en línea recta en LOITER a 2.3 m, o deja el dron en vuelo estacionario (modo '
                     'estático). Los escenarios son: (a) avance hacia un panel fijo de 2 × 2.6 m a 1, 2, 3 y 4 m/s; (b) '
                     'avance hacia una persona quieta a 1.5 y 3 m/s; (c) persona que viene de frente caminando (1.4 m/s) '
                     'o corriendo (3.3 m/s), con avance a 1 m/s; (d) persona que cruza lejos, caminando o corriendo, que '
                     'no debe activar el sistema; y (e) modo estático, con una persona que viene caminando o corriendo y '
                     'con otra que pasa de lado a 5 m, que tampoco debe activarlo. En campo, las personas de los '
                     'escenarios (b) y (c) se reemplazan primero por un maniquí.')
    q = M.parrafo(q, 'Un vuelo es exitoso si, cuando el escenario pide activarse, el sistema se activa y no hay choque, '
                     'y si, cuando no lo pide, no se activa y no hay choque. Además se registran las activaciones '
                     'verdaderas y falsas, los eventos de riesgo, la latencia entre el riesgo y la orden, el tiempo hasta '
                     'el frenado efectivo y las paradas del operador. Para comparar la decisión por reglas con la decisión '
                     'del clasificador se usan cinco escenarios de discriminación con personas que pasan cerca de la '
                     'trayectoria; en ellos el éxito se juzga contra lo que habría pasado en el mismo vuelo sin el '
                     'sistema. La {F:secuencia} resume el orden de las pruebas.')
    cap = M.rotulo(q, 'Figura', 'secuencia', 'Secuencia de validación, de la simulación al campo')
    fig = M.figura(cap, f'{DIAG}/03_experimento.png', ancho_cm=15.5)
    q = M.parrafo(fig, '2.3.2 Origen de los valores numéricos del sistema', AMARILLO, ppr_de=P[484])
    q = M.parrafo(q, 'Cada número del sistema tiene una razón física o se eligió con datos que no se usan para '
                     'evaluarlo. La {T:valores} los reúne.')
    cap = M.rotulo(q, 'Tabla', 'valores', 'Valores del sistema y su justificación')
    tv = M.tabla(cap, filas_v, [2.3, 4.0, 9.7])
    q = M.parrafo(tv, '2.3.3 Decisión con inteligencia artificial dentro de reglas de seguridad', AMARILLO,
                  ppr_de=P[484])
    q = M.parrafo(q, 'Detectar a una persona en una imagen no se puede resolver con condicionales; por eso se usa YOLO. '
                     'La pregunta es si, una vez detectada, hace falta una IA para decidir si intervenir. Las medidas '
                     'reales son ruidosas: la distancia estimada con el tamaño de la caja se equivoca hasta el doble a '
                     'corta distancia, YOLO pierde cuadros y una persona que cruza delante puede parecerse por un '
                     'instante a una que viene de frente. Con umbrales fijos hay que escoger entre frenar de más o frenar '
                     'de menos. El clasificador aprende la frontera de decisión combinando las quince medidas a la vez.')
    q = M.parrafo(q, 'Las reglas no desaparecen: quedan como una envolvente que garantiza un comportamiento verificable. '
                     'El bloqueo frontal por LiDAR, el árbitro que autoriza el ascenso y la parada del operador mandan '
                     'sobre la IA. Así la IA aporta criterio donde las reglas fijas son ineficientes, y las reglas '
                     'responden donde la IA podría fallar.')
    q = M.parrafo(q, '2.3.4 Análisis de los datos', AMARILLO, ppr_de=P[484])
    q = M.parrafo(q, 'El análisis cuantitativo usa las métricas del protocolo. Las tasas de éxito se reportan con el '
                     'intervalo de confianza del 95 % de Wilson, adecuado para muestras pequeñas y proporciones cercanas '
                     'a 0 o a 100 % (Wilson, 1927). En simulación se hacen 100 vuelos por variante; en campo, diez '
                     'repeticiones por escenario. Para comparar dos formas de decidir sobre los mismos vuelos se usa la '
                     'prueba de McNemar, que solo cuenta los vuelos en que difieren (McNemar, 1947); es la adecuada porque '
                     'en simulación cada decisor enfrenta exactamente los mismos mundos.')
    q = M.parrafo(q, 'El análisis cualitativo parte de la observación técnica registrada en la bitácora y en el video de '
                     'cada ensayo. Se describen cuatro aspectos: la estabilidad de la aeronave durante la maniobra, el '
                     'comportamiento del piloto al retomar el mando, el efecto del viento y la iluminación sobre la '
                     'detección, y las fallas o comportamientos inesperados. Estas observaciones explican los números y '
                     'ayudan a decidir si una falla viene del sensor, de la decisión o del control.')

    q = M.parrafo(q, '2.3.5 Preparación de la jornada y criterios de seguridad', AMARILLO, ppr_de=P[484])
    q = M.parrafo(q, 'Antes de cada jornada se revisa la lista siguiente; si un punto no se cumple, no se vuela.', AMARILLO)
    for t in ['Zona consultada en el Visor Geográfico UAS, sin restricciones; permiso del dueño del terreno.',
              'Pronóstico revisado; viento medido con anemómetro por debajo del límite fijado [FALTA: límite de viento en '
              'm/s].', 'Zona delimitada y señalizada; ningún tercero dentro de ella.',
              'Batería cargada y medida (tensión por celda); batería de repuesto en bolsa ignífuga.',
              'Hélices, tornillos y amarres revisados; estabilizador y LiDAR firmes.',
              'Geocerca de ArduPilot activa; LOIT_SPEED en 4 m/s; modos del interruptor comprobados.',
              'Parada de emergencia (CH8) probada en tierra antes de cada vuelo.',
              'Registro de la Jetson y DataFlash funcionando; reloj del sistema sincronizado.',
              'Fijación GPS 3D antes de activar el modo experimental.',
              'Piloto de seguridad y observador presentes; consentimientos firmados de los voluntarios.']:
        q = M.vineta(q, t)
    q = M.parrafo(q, 'El campo es abierto y plano, sin público. Un panel de 2 × 2.6 m (cartón pluma o lona sobre un marco) '
                     'se coloca a 20 m del punto de partida, y sobre la trayectoria se ponen conos a 2, 4, 6, 8, 10, 12 y '
                     '15 m, medidos con cinta, para estimar distancias en el video. Primero se usa un maniquí o una '
                     'silueta de 1.7 m; una persona real solo después de diez éxitos de diez con el maniquí, y siempre con '
                     'la parada de emergencia en la mano del operador. La {F:campofoto} muestra el montaje usado para '
                     'grabar datos reales de los sensores: el cuadricóptero, sin hélices, se apoya sobre un vehículo, y un '
                     'computador portátil conectado por SSH registra los datos. [FALTA: fecha, lugar y qué se probó en '
                     'cada foto; confirmar que el conjunto residencial autorizó grabar y publicar estas imágenes]',
                  AMARILLO)
    cap = M.rotulo(q, 'Figura', 'campofoto', 'Montaje para grabar datos reales de los sensores')
    fig = M.figura(cap, os.path.join(FOTOS, 'campo_exterior.jpg'), ancho_cm=15.5, color=AMARILLO)
    q = M.nota(fig, 'Nota. A la izquierda, el cuadricóptero sin hélices sobre el vehículo, con el portátil conectado; a la '
                    'derecha, el tramo de la prueba, con una marca negra en el suelo como referencia de distancia. Se '
                    'difuminó la placa del vehículo.')
    q = M.parrafo(q, 'La jornada se interrumpe en cualquiera de estos casos:', AMARILLO)
    for t in ['Viento por encima del límite o lluvia.', 'Un tercero entra en la zona.',
              'Batería por debajo de 3.5 V por celda o aviso de failsafe.',
              'Comportamiento inesperado del dron o pérdida del enlace MAVLink.',
              'Cualquier contacto con una persona, el maniquí o el panel: se suspende la jornada y se analiza el '
              'registro antes de seguir.']:
        q = M.vineta(q, t)

    # =================================================================== 3 resultados
    filas_lat = [
        ['Escenario', 'Riesgo → orden (s)', 'Orden → frenado (s)', 'Distancia mínima (m)'],
        ['a) Panel, 1 m/s', '0.09 [0.08, 0.10]', '0.59 [0.58, 0.60]', '1.77 [1.73, 1.82]'],
        ['a) Panel, 4 m/s', '0.10 [0.09, 0.11]', '1.39 [1.38, 1.39]', '5.35 [5.30, 5.40]'],
        ['b) Persona quieta, 3 m/s', '0.10 [0.07, 0.12]', '1.12 [1.11, 1.13]', '6.44 [6.38, 6.51]'],
        ['c) Persona que corre de frente', '0.11 [0.10, 0.13]', '0.58 [0.57, 0.59]', '5.65 [5.57, 5.72]'],
        ['e) Estático, persona que corre', '0.12 [0.09, 0.14]', '— (quieto)', '6.12 [6.05, 6.20]'],
    ]
    filas_disc = [
        ['Escenario de discriminación', '¿Debe activarse?', 'Reglas', 'IA con reglas'],
        ['Cruza 3–4 m por delante y sigue', 'no', '95 %', '98 %'],
        ['Cruza justo por donde pasa el dron', 'sí', '65 %', '77 %'],
        ['Viene de frente a 3 m del costado', 'no', '96 %', '95 %'],
        ['Viene de frente a 1 m del costado', 'sí', '100 %', '100 %'],
        ['Camina delante, más rápido que el dron', 'no', '100 %', '100 %'],
        ['Total (500 vuelos)', '', '91.2 % [88.4, 93.4]', '94.0 % [91.6, 95.8]'],
    ]
    filas_metr = [
        ['Métrica', 'Reglas', 'IA con reglas', 'Experimento', 'Prueba'],
        ['Éxito en el protocolo del comité', '100 %', '100 %', '1300 vuelos', 'Sin diferencia'],
        ['Éxito en discriminación', '91.2 %', '94.0 %', '500 vuelos', 'McNemar: 16 contra 2, p = 0.0013'],
        ['Activaciones innecesarias', '44', '30', '1800 vuelos', 'McNemar: 16 contra 2, p = 0.0013'],
        ['Personas a < 2 m bajo 3.30 m', '420', '218', '3840 vuelos', 'p < 0.001'],
        ['Choques', '39', '28', '3840 vuelos', 'p ≈ 0.18 (no significativa)'],
    ]
    filas_campo = [
        ['Escenario', 'Repeticiones', 'Éxitos', 'IC de Wilson 95 %', 'Latencia (ms)', 'Intervenciones del operador'],
        ['a) Panel de cartón, 1 m/s', '10', '[FALTA]', '[FALTA]', '[FALTA]', '[FALTA]'],
        ['a) Panel de cartón, 2 m/s', '10', '[FALTA]', '[FALTA]', '[FALTA]', '[FALTA]'],
        ['b) Maniquí quieto', '10', '[FALTA]', '[FALTA]', '[FALTA]', '[FALTA]'],
        ['c/e) Voluntario que se acerca caminando', '10', '[FALTA]', '[FALTA]', '[FALTA]', '[FALTA]'],
        ['d) Persona que cruza lejos', '10', '[FALTA]', '[FALTA]', '[FALTA]', '[FALTA]'],
    ]
    h3 = next(p for p in P[550:570] if p.text.strip() == '3. Resultados')
    q = M.parrafo(h3, 'Los resultados siguen el orden de la {F:secuencia}: primero la simulación del protocolo, después '
                      'la comparación entre formas de decidir y, al final, las pruebas en banco y en campo.')
    q = M.parrafo(q, '3.1 Protocolo del comité en simulación', AMARILLO, ppr_de=P[481])
    q = M.parrafo(q, 'Con el sistema activo, los 1300 vuelos del protocolo (13 variantes de 100 vuelos) terminaron con '
                     'éxito: 100.0 % [99.7, 100.0]. Sin el sistema, con el operador solo, apenas el 23 % [21, 25] de los '
                     'vuelos fue seguro. No hubo activaciones falsas en los 300 vuelos que no debían activarlo. El '
                     'operador apretó la parada en 28 vuelos, todos con la persona que corre hacia el dron, y ninguno '
                     'terminó en choque. La {T:protocolo} da el resultado de cada variante y la {T:latencias} las latencias y '
                     'distancias principales.')
    from datos_tablas import PROTOCOLO, MUNDOS, DEGRADADAS, VELOCIDADES
    cap = M.rotulo(q, 'Tabla', 'protocolo', 'Resultados del protocolo del comité en simulación (100 vuelos por variante)')
    t = M.tabla(cap, PROTOCOLO, [4.6, 1.5, 2.8, 2.6, 2.4, 2.1])
    q = M.nota(t, 'Nota. Entre corchetes, intervalo de Wilson del 95 %. "Sin ayuda del operador": el operador no apretó la '
                  'parada en ningún momento.')
    q = M.parrafo(q, 'En las 13 variantes el sistema termina con éxito y sin choques. Sin él, todos los escenarios que piden '
                     'activarse terminan en riesgo físico, y las personas que vienen de frente producen entre 98 y 100 '
                     'choques de cada 100 vuelos. En los escenarios que no deben activarlo (persona que cruza lejos o pasa '
                     'de lado) el sistema tampoco se activa, y el vuelo es seguro con y sin él. El único caso en que el '
                     'operador por sí solo no basta es la persona que corre de frente: sin ayuda del sistema, solo el 72 % '
                     'de los vuelos sale bien. La {T:latencias} da las latencias y distancias de los escenarios '
                     'principales.', AMARILLO)
    cap = M.rotulo(q, 'Tabla', 'latencias', 'Latencias y distancias mínimas en simulación')
    t = M.tabla(cap, filas_lat, [5.0, 3.6, 3.6, 3.6])
    q = M.nota(t, 'Nota. Media e intervalo del 95 % de 100 vuelos por escenario.')
    q = M.parrafo(q, '3.2 Decisión por reglas frente a decisión con IA', AMARILLO, ppr_de=P[481])
    q = M.parrafo(q, 'En el protocolo del comité las dos formas de decidir logran 100 % de éxito y ningún choque: los '
                     'escenarios son claros y las reglas ya los resuelven. La diferencia aparece cuando una persona pasa '
                     'cerca de la trayectoria ({T:disc}). La IA con reglas acertó en el 94.0 % de los vuelos frente al '
                     '91.2 % de las reglas solas, y bajó las activaciones innecesarias de 44 a 30 en 1800 vuelos. En los '
                     'vuelos en que los dos decisores no coinciden, la IA acierta y las reglas fallan 16 veces, y lo '
                     'contrario ocurre 2 veces (McNemar, p = 0.0013).')
    cap = M.rotulo(q, 'Tabla', 'disc', 'Éxito por escenario de discriminación (100 vuelos cada uno)')
    t = M.tabla(cap, filas_disc, [6.6, 2.8, 3.2, 3.4])
    q = M.parrafo(t, 'La {F:g1} muestra la diferencia por escenario: la IA gana en los dos casos más difíciles (cruce justo por '
                     'la trayectoria, 77 % contra 65 %, y cruce por delante, 98 % contra 95 %), empata en los claros y pierde '
                     'un punto cuando la persona viene de frente a 3 m del costado (95 % contra 96 %).', AMARILLO)
    cap = M.rotulo(q, 'Figura', 'g1', 'Éxito por escenario de discriminación: reglas solas frente a IA con reglas')
    fig = M.figura(cap, f'{DIAG}/g1_discriminacion.png', ancho_cm=15.5, color=AMARILLO)
    q = M.parrafo(fig, 'En 3840 vuelos sobre mundos aleatorios que no se usaron ni para entrenar ni para elegir el umbral, '
                     'la IA con reglas redujo los vuelos con una persona a menos de 2 m del dron por debajo de 3.30 m de '
                     '420 a 218 y las activaciones innecesarias de 137 a 67. Los choques pasaron de 39 a 28, una '
                     'diferencia que no es estadísticamente significativa ({T:metricas}). La {T:mundos} da el detalle por decisor. Con el piloto a 4 m/s o menos, '
                     'la velocidad recomendada, los riesgos no evitados son prácticamente los mismos (24 con la IA y 22 '
                     'con las reglas): en la operación recomendada la ventaja de la IA es la eficiencia, no una seguridad '
                     'mayor.')
    cap = M.rotulo(q, 'Tabla', 'mundos', 'Resultados en 3840 vuelos sobre 60 mundos aleatorios de prueba')
    t = M.tabla(cap, MUNDOS, [3.2, 2.6, 1.8, 3.0, 2.8, 2.6])
    q = M.nota(t, 'Nota. 2043 de los 3840 vuelos (53 %) habrían tenido riesgo físico sin el sistema. Incluye casos '
                  'físicamente imposibles de evitar.')
    q = M.parrafo(q, 'La {F:g2} compara los dos decisores: la IA con reglas deja casi a la mitad los vuelos con una persona '
                     'cerca (de 420 a 218) y las activaciones innecesarias (de 137 a 67), mientras que los riesgos no '
                     'evitados bajan menos (de 92 a 67) y los choques, de 39 a 28.', AMARILLO)
    cap = M.rotulo(q, 'Figura', 'g2', 'Resultados de los dos decisores en 3840 vuelos sobre mundos aleatorios')
    q = M.figura(cap, f'{DIAG}/g2_mundos.png', ancho_cm=15.5, color=AMARILLO)
    cap = M.rotulo(q, 'Tabla', 'metricas', 'Métricas principales y prueba estadística')
    t = M.tabla(cap, filas_metr, [4.6, 1.9, 2.4, 2.6, 4.5])
    q = M.nota(t, 'Nota. Cada experimento usa vuelos distintos; no se deben mezclar sus cifras. Las pruebas de los 3840 '
                  'vuelos comparan proporciones sin emparejar.')
    q = M.parrafo(q, '3.3 Condiciones degradadas', AMARILLO, ppr_de=P[481])
    q = M.parrafo(q, 'A las velocidades del protocolo ninguna degradación realista hizo fallar el sistema: pérdida de '
                     'detecciones, oclusión de medio cuerpo, ruido del LiDAR, latencias de 200 y 300 ms y viento de cola '
                     'de 3 y 5 m/s. Los límites aparecen al subir la velocidad o con solo la cabeza y los hombros '
                     'visibles, caso en el que la detección llega tarde incluso a 1 m/s. La {T:degr} da el éxito, los choques y las '
                     'activaciones innecesarias de cada decisor en 14 condiciones con sensores degradados.')
    cap = M.rotulo(q, 'Tabla', 'degr', 'Desempeño con sensores degradados (18 variantes de 100 vuelos por condición)')
    t = M.tabla(cap, DEGRADADAS, [6.0, 5.0, 5.0])
    q = M.nota(t, 'Nota. Combinada: recall 0.85, medio cuerpo, LiDAR degradado, 200 ms y viento de 4 m/s.')
    q = M.parrafo(q, 'Con las reglas solas, el éxito va de 97.6 % en la condición nominal a 96.8 % en la combinada; con la IA '
                     'y las reglas, de 98.3 % a 98.0 %. No hubo choques en ninguna condición salvo cuando solo se ve la '
                     'cabeza y los hombros (C12), donde cada decisor tuvo uno. La ventaja de la IA se pierde justo cuando el '
                     'detector falla más: con un recall de 0.40 los dos aciertan 97.4 % de los vuelos, y con solo cabeza y '
                     'hombros la IA queda en 96.5 % frente a 96.9 % de las reglas. La {F:g3} muestra el éxito de cada '
                     'decisor en las 14 condiciones.', AMARILLO)
    cap = M.rotulo(q, 'Figura', 'g3', 'Éxito por condición con sensores degradados')
    fig = M.figura(cap, f'{DIAG}/g3_degradadas.png', ancho_cm=15.5, color=AMARILLO)
    q = M.nota(fig, 'Nota. El eje vertical empieza en 94 %. C0 es la condición nominal y C10, la combinada.')
    q = M.parrafo(q, 'La {T:veloc} da la velocidad máxima de avance con margen en las condiciones más exigentes.',
                  AMARILLO)
    cap = M.rotulo(q, 'Tabla', 'veloc', 'Velocidad máxima de avance (m/s) a la que las reglas detienen el dron con margen')
    t = M.tabla(cap, VELOCIDADES, [6.0, 3.0, 3.0, 4.0])
    q = M.nota(t, 'Nota. Barrido de 1 a 12 m/s; segura si esa velocidad y todas las menores cumplen en al menos el 95 % de '
                  'los vuelos. Con IA y reglas, frente a una persona quieta, sube a 12 m/s.')
    q = M.parrafo(q, 'Frente a un panel fijo las reglas detienen el dron con margen hasta 10 u 11 m/s, pero frente a una '
                     'persona quieta el límite es de 4 m/s en todas las condiciones, y frente a una persona que corre baja '
                     'hasta 0 m/s cuando solo se ven la cabeza y los hombros. Por eso el piloto se limita a 4 m/s '
                     '(LOIT_SPEED), como lo resume la {F:g4}.', AMARILLO)
    cap = M.rotulo(q, 'Figura', 'g4', 'Velocidad máxima segura de avance según la condición y el obstáculo')
    q = M.figura(cap, f'{DIAG}/g4_velocidades.png', ancho_cm=15.5, color=AMARILLO)
    q = M.parrafo(q, '3.4 Pruebas en banco', AMARILLO, ppr_de=P[481])
    q = M.parrafo(q, 'El plan de pruebas físicas tiene cinco pasos, de menor a mayor riesgo ({T:planbanco}). [FALTA: '
                     'resultado de cada paso, con fotos del montaje]')
    filas_plan = [['Paso', 'Prueba en banco', 'Criterio de aceptación', 'Resultado'],
                  ['1', 'Cuadros por segundo sostenidos durante 10 minutos', 'Sin congelamientos ni caídas de cuadros', '[FALTA]'],
                  ['2', 'Lecturas del LiDAR en movimiento', 'Sin huecos prolongados en la señal', '[FALTA]'],
                  ['3', 'Latencia entre el riesgo y la orden, medida en el registro', 'Menos de 150 ms', '[FALTA]'],
                  ['4', 'Retoma del piloto con el interruptor de modos', 'La Jetson suelta el mando y no vuelve a pedir GUIDED', '[FALTA]'],
                  ['5', 'Clasificador en modo sombra', 'Decide en banco igual que en simulación', '[FALTA]']]
    cap = M.rotulo(q, 'Tabla', 'planbanco', 'Plan de pruebas en banco y su resultado')
    t = M.tabla(cap, filas_plan, [1.2, 6.2, 6.0, 2.1])
    q = M.nota(t, 'Nota. El criterio de latencia sale de la {T:valores}.')
    q = M.parrafo(q, '3.5 Ensayos de campo', AMARILLO, ppr_de=P[481])
    q = M.parrafo(q, 'La {T:campo} resume los ensayos de campo por escenario. [FALTA: fecha, hora, viento medido e '
                     'iluminación de cada jornada]')
    cap = M.rotulo(q, 'Tabla', 'campo', 'Resultados de campo por escenario')
    t = M.tabla(cap, filas_campo, [4.4, 2.1, 1.7, 2.6, 2.4, 2.8])
    q = M.parrafo(t, '3.6 Observaciones cualitativas', AMARILLO, ppr_de=P[481])
    q = M.parrafo(q, '[FALTA: lo observado en la bitácora y en el video de cada ensayo, según los cuatro aspectos de '
                     '2.3.4: estabilidad durante la maniobra, retoma del piloto, efecto del viento y de la luz, y fallas '
                     'o comportamientos inesperados]')
    q = M.parrafo(q, '3.7 Discusión', AMARILLO, ppr_de=P[481])
    q = M.parrafo(q, 'La simulación indica que el sistema cumple el protocolo y que la decisión con IA dentro de reglas '
                     'mejora la discriminación sin perder seguridad. Esto responde a la brecha que señalan Vera-Yanez et '
                     'al. (2023), pero solo en parte: el detector se modeló estadísticamente y no con imágenes reales, '
                     'así que la validez de esas cifras depende de que los ensayos de campo las confirmen. La {T:supuestos} '
                     'reúne los supuestos del simulador y la prueba con la que cada uno se comprobará en campo.')
    filas_sup = [['Supuesto del simulador', 'Valor', 'Cómo se comprobará en campo'],
                 ['Detector', 'Probabilidad de detección que cae con la distancia; ruido en el rumbo', 'Comparar las detecciones reales con las del modelo estadístico (3.4 y 3.5)'],
                 ['Distancia a la persona', 'Estimada con la altura de la caja, suponiendo 1.72 m de estatura', 'Medir con marcas en el suelo y con el LiDAR cuando el rayo toca a la persona'],
                 ['LiDAR', 'Un rayo de 0.1 a 30 m, 2 cm de ruido, inclinado −5°', 'Registrar la señal real del TF03 en el carrito y en vuelo'],
                 ['Retardo de las medidas', '100 ms', 'Medir la latencia entre el riesgo y la orden en el registro de la Jetson'],
                 ['Control del dron', 'Controladores de posición y actitud de ArduPilot modelados', 'Medir la distancia de frenado real en los ensayos'],
                 ['Personas', 'Caminan a 1.4 m/s y corren a 3.3 m/s', 'Cronometrar a los voluntarios en cada repetición']]
    cap = M.rotulo(q, 'Tabla', 'supuestos', 'Supuestos del simulador y su comprobación en campo')
    t = M.tabla(cap, filas_sup, [3.4, 6.0, 6.1])
    q = M.parrafo(t, 'La {T:cumple} resume qué se logró en cada objetivo específico, con su evidencia y lo que falta.',
                  AMARILLO)
    filas_obj = [['Objetivo específico', 'Qué se logró', 'Evidencia', 'Lo que falta'],
                 ['1. Definir la arquitectura operativa', 'Arquitectura de percepción, decisión y control con YOLO26n, LiDAR TF03, Jetson Orin Nano y Pixhawk', 'Requerimientos, matrices de decisión y diagramas de 2.1; arquitectura de 2.2.6', '[FALTA: latencia total del ciclo medida]'],
                 ['2. Evaluar la integración funcional', 'Activación, comunicación y respuesta del detector verificadas en tierra', 'Tablas de 2.2.7 y de verificación de requerimientos', '[FALTA: cambio a GUIDED y retoma del piloto en banco]'],
                 ['3. Validar el protocolo de evasión', 'Protocolo cumplido en simulación en 1300 vuelos; IA con reglas mejor que las reglas en casos dudosos', 'Capítulo 3 (3.1 a 3.3)', '[FALTA: ensayos de campo con su intervalo de confianza]']]
    cap = M.rotulo(q, 'Tabla', 'cumple', 'Cumplimiento de los objetivos específicos')
    t = M.tabla(cap, filas_obj, [3.4, 5.0, 3.8, 3.3])
    q = M.parrafo(t, '[FALTA: comparar cada escenario de campo con su intervalo de simulación y explicar las diferencias '
                     '(sensor, latencia o viento)]')

    # =================================================================== 4 y 5
    M.marcar(P[560])
    q = P[561]
    for t in [
        'Primer objetivo. Se definió una arquitectura de percepción, decisión y control con un detector YOLO '
        'preentrenado, un LiDAR frontal, una computadora de a bordo Jetson Orin Nano y una controladora Pixhawk. La '
        'selección por matrices de decisión eligió al principio una Raspberry Pi; las pruebas de integración mostraron '
        'que su capacidad estaba sobreestimada y se cambió a la Jetson. [FALTA: latencia total del ciclo medida]',
        'Segundo objetivo. Se verificaron en la aeronave la activación (arranque con alimentación propia y detección '
        'continua), la comunicación (LiDAR a 100 Hz y MAVLink a 115200 baudios con confirmación) y la respuesta del '
        'detector ante personas en movimiento. [FALTA: cambio a GUIDED y retoma del piloto en banco]',
        'Tercer objetivo. En simulación el protocolo se cumplió en el 100 % de 1300 vuelos, y la decisión con IA dentro '
        'de reglas fue más precisa que las reglas solas en los casos dudosos (94.0 % frente a 91.2 %, p = 0.0013). '
        '[FALTA: conclusión con la tasa de éxito de campo y su intervalo de confianza]',
        '[FALTA: conclusión general de uno o dos párrafos que responda la pregunta de investigación de 1.3]']:
        q = M.parrafo(q, t)
    p5 = next(p for p in P[555:600] if p.text.strip() == '5. Recomendaciones')
    q = p5
    for t in [
        'Instalar un filtro IR-cut en la cámara antes de los ensayos con sol: sin él la imagen muestra una cuadrícula de '
        'manchas y un tinte morado.',
        'Ampliar los ensayos de campo a 35 repeticiones por escenario si se quiere afirmar un éxito de al menos 90 % con '
        '95 % de confianza.',
        'Reentrenar el clasificador con datos reales y simulados si en modo sombra decide distinto que en simulación.',
        'Repetir la simulación del protocolo antes de mover el LiDAR o de agregar un segundo sensor, porque el '
        'clasificador se entrenó con el TF03 alineado con la cámara a −5°.',
        'Evaluar si el ascenso de protección debe esperar la autorización del árbitro: por encima de 4 m/s ese veto es '
        'la principal fuente de aproximaciones a menos de 2 m.',
        'Como trabajo futuro, extender el sistema a la búsqueda y el seguimiento de una persona designada por el '
        'operador; en simulación ya se entrenó una política de refuerzo (PPO) para esa tarea, fuera del alcance '
        'aprobado.']:
        q = M.vineta(q, t)
