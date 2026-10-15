"""Capítulo 2 · 2.2 integración, 2.3 protocolo; capítulos 3 a 5."""
import copy
from docx.oxml.ns import qn
from docx.text.run import Run

from motor import AMARILLO, ROJO, TURQ, ROSA, VERDE


def aplicar(M, reescribir, mover, DIAG):
    P, T = M.P, M.T
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
        'sentido antihorario y 3 y 4 en sentido horario. La masa medida fue de 2371 g ({F:fC1}, Anexo C). [FALTA: aclarar qué incluye esa '
        'medición y calcular la relación empuje–peso]'])
    reescribir([487], ['La {F:dron} muestra la aeronave ensamblada. El inventario de componentes está en el Anexo C.'])
    M.marcar(P[490])

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
    M.marcar(P[502])
    reescribir([505], [
        'La {F:mp} muestra la pantalla de vuelo de Mission Planner con la aeronave en tierra: el horizonte artificial '
        'responde a la inclinación del chasis, el modo y el estado de armado se actualizan y no aparecen mensajes de '
        'prearmado, lo que indica que la controladora lee sus sensores y atiende al radiocontrol.'])
    M.marcar(P[508])

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
        'de flujo está en el Anexo E.'])
    reescribir([518], [
        'Antes de instalarlo en la aeronave, el detector se probó en un computador portátil con su cámara integrada y luz '
        'artificial ({F:detector}). Así se descartaron errores de lógica y de configuración sin las restricciones de '
        'energía del sistema embebido.'])
    reescribir([522], [
        'Nota. La persona que aparece autorizó el uso de su imagen con fines académicos. [FALTA: reemplazar por una '
        'captura del detector YOLO de personas (la ventana actual dice "Detección de Rostros") y confirmar por escrito la '
        'autorización de la persona]'])
    mover([523, 524, 525, 526, 527, 528], 'E', 'figE1')

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
    reescribir([538], [
        'El código se organiza en módulos, uno por archivo; su organización y los listados principales están en el '
        'Anexo E. En el cuerpo del documento solo se presentan la arquitectura ({F:arq}) y los estados de la maniobra '
        '({F:estados}).'])
    for i in (539, 540, 541):
        M.marcar(P[i])
    cap = M.rotulo(P[541], 'Figura', 'arq', 'Arquitectura de percepción, decisión y control')
    fig = M.figura(cap, f'{DIAG}/01_arquitectura.png', alto_max=17.0)
    reescribir([542], [
        'La cámara alimenta a la IA 1, el detector YOLO26n con seguimiento. El estabilizador no sigue a la persona: '
        'mantiene la cámara y el LiDAR con una inclinación fija de −5°, de modo que el LiDAR mide lo que hay al frente, '
        'en la trayectoria. De cada cuadro se calculan quince entradas para la IA 2: de la caja de YOLO, el alto, el '
        'ancho, el área, el ángulo horizontal y su variación, la confianza y el número de cuadros seguidos con detección; '
        'del LiDAR, la distancia y si la lectura es utilizable; de la Pixhawk, la velocidad que estima su filtro EKF; y '
        'de un seguimiento alfa-beta de la persona, la distancia, la velocidad de acercamiento, la velocidad lateral y el '
        'tiempo sin detección. Las entradas se calculan con la misma función en la simulación y en el dron, para que el '
        'modelo reciba en vuelo lo mismo que vio al entrenarse.'])
    reescribir([543], [
        'La IA 2 es un perceptrón multicapa de scikit-learn con dos capas ocultas de 32 y 16 neuronas (ReLU) y una sola '
        'salida: la probabilidad de que, si el piloto mantiene su mando, en los próximos 3 s ocurra un choque o una '
        'persona quede a menos de 2 m del dron. Si esa probabilidad supera 0.7 durante 2 cuadros seguidos, el sistema '
        'pasa de CONTINUAR a DETENER_Y_ASCENDER. No hay salidas de evasión lateral, lo que respeta la limitación de '
        '1.4.2. El modelo se entrenó con 2 551 725 cuadros de vuelos simulados (13 % con riesgo), etiquetados '
        'automáticamente con la verdad del simulador, y se probó con 533 085 cuadros de mundos que no participaron en '
        'el entrenamiento: área bajo la curva ROC de 0.974 y 0.3 % de falsos positivos por cuadro. El umbral y el número '
        'de cuadros se eligieron con mundos de validación, nunca con el protocolo. Los detalles del entrenamiento están '
        'en el Anexo F. [FALTA: validar el clasificador con datos reales del dron (pasos 4 y 5 del plan de pruebas) y '
        'reportar el resultado]'])
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
    fig = M.figura(cap, f'{DIAG}/02_estados.png', alto_max=14.0)
    M.nota(fig, 'Nota. CH5: modo de vuelo; CH7: interruptor del modo experimental; CH8: parada de emergencia.')
    reescribir([545], [
        'La orden llega a la Pixhawk por MAVLink en el modo GUIDED, que exige posición GPS con fijación 3D (ArduPilot, '
        's. f.-b). En la secuencia prevista, el piloto despega y vuela en LOITER a 2.3 m, activa el modo experimental '
        'con un interruptor del radiocontrol y avanza. Solo cuando el sistema decide intervenir, la Jetson cambia la '
        'Pixhawk a GUIDED, anula la velocidad horizontal y ordena subir hasta 3.30 m con una consigna de posición, que '
        'GUIDED sostiene por sí mismo. El piloto retoma el mando moviendo el interruptor de modos; si la Jetson deja de '
        'enviar consignas, el parámetro GUID_TIMEOUT hace que la Pixhawk frene sola. Cada ejecución escribe un registro '
        'CSV con el modo, el armado, la altura, el voltaje, el estado de la decisión, la distancia y su fuente, la '
        'probabilidad, las órdenes enviadas y las latencias (RF-09). Los parámetros de ArduPilot y del software están en '
        'el Anexo D.'])

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
        'menos de 150 ms); la grabación de datos reales con el dron sin hélices sobre un vehículo ({F:fG1}, Anexo G), para comparar '
        'los sensores con su modelo de simulación; el clasificador en modo sombra, que decide y registra pero no manda; y la '
        'fijación GPS 3D que exige GUIDED. [FALTA: resultado de estas cinco comprobaciones]'])
    reescribir([557], [
        'Las pruebas siguientes van de menor a mayor riesgo: ejecución en banco sin la Pixhawk, que muestra qué '
        'decidiría el sistema sin enviar nada; ejecución en banco con la Pixhawk conectada y sin hélices, para comprobar '
        'el cambio de modo y la retoma del piloto; y simulación del lazo MAVLink en el simulador SITL de ArduPilot. Solo '
        'después se pasa al vuelo exterior, con observador y piloto de seguridad, según el protocolo de 2.3 y las listas '
        'del Anexo G.'])

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
    q = M.parrafo(P[557], '2.3 Protocolo de validación experimental', AMARILLO, ppr_de=P[481])
    q = M.parrafo(q, 'Para el tercer objetivo se definió un protocolo con los mismos escenarios en simulación y en '
                     'campo. La simulación sirvió para fijar los parámetros iniciales de operación y los criterios de '
                     'seguridad, como prevé el alcance de 1.4.1, antes de arriesgar la aeronave; los vuelos de campo '
                     'validan el sistema real. El modelo de simulación y sus resultados completos están en el Anexo F.')
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
    fig = M.figura(cap, f'{DIAG}/03_experimento.png', ancho_cm=14.5)
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
                     'terminó en choque. La {T:latencias} muestra las latencias y distancias principales; el detalle por '
                     'escenario está en el Anexo F.')
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
    q = M.parrafo(t, 'En 3840 vuelos sobre mundos aleatorios que no se usaron ni para entrenar ni para elegir el umbral, '
                     'la IA con reglas redujo los vuelos con una persona a menos de 2 m del dron por debajo de 3.30 m de '
                     '420 a 218 y las activaciones innecesarias de 137 a 67. Los choques pasaron de 39 a 28, una '
                     'diferencia que no es estadísticamente significativa ({T:metricas}). Con el piloto a 4 m/s o menos, '
                     'la velocidad recomendada, los riesgos no evitados son prácticamente los mismos (24 con la IA y 22 '
                     'con las reglas): en la operación recomendada la ventaja de la IA es la eficiencia, no una seguridad '
                     'mayor.')
    cap = M.rotulo(q, 'Tabla', 'metricas', 'Métricas principales y prueba estadística')
    t = M.tabla(cap, filas_metr, [4.6, 1.9, 2.4, 2.6, 4.5])
    q = M.nota(t, 'Nota. Cada experimento usa vuelos distintos; no se deben mezclar sus cifras. Las pruebas de los 3840 '
                  'vuelos comparan proporciones sin emparejar.')
    q = M.parrafo(q, '3.3 Condiciones degradadas', AMARILLO, ppr_de=P[481])
    q = M.parrafo(q, 'A las velocidades del protocolo ninguna degradación realista hizo fallar el sistema: pérdida de '
                     'detecciones, oclusión de medio cuerpo, ruido del LiDAR, latencias de 200 y 300 ms y viento de cola '
                     'de 3 y 5 m/s. Los límites aparecen al subir la velocidad o con solo la cabeza y los hombros '
                     'visibles, caso en el que la detección llega tarde incluso a 1 m/s. Las tablas completas están en '
                     'el Anexo F.')
    q = M.parrafo(q, '3.4 Pruebas en banco', AMARILLO, ppr_de=P[481])
    q = M.parrafo(q, '[FALTA: resultados de los pasos 1 a 5 del plan de pruebas físicas: cuadros por segundo sostenidos '
                     'durante 10 minutos, huecos del LiDAR, latencia entre el riesgo y la orden medida en el registro, '
                     'retoma del piloto con el interruptor de modos y comparación del clasificador en modo sombra con la '
                     'simulación, con fotos del montaje]')
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
                     'así que la validez de esas cifras depende de que los ensayos de campo las confirmen. [FALTA: '
                     'comparar cada escenario de campo con su intervalo de simulación y explicar las diferencias '
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
