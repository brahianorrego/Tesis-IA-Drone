"""Datos de tablas que se reutilizan entre el cuerpo y los anexos."""

ANCLAS = [
            ['Nivel', 'Función 1: sensores', 'Función 2: procesamiento y potencia', 'Función 3: control y seguridad'],
            ['1', 'Inoperante al aire libre', 'Sin sistema operativo embebido', 'Integración bloqueada (código cerrado)'],
            ['2', 'Falla constante con el clima', 'No puede ejecutar redes neuronales', 'Método invasivo que anula las '
             'alertas del autopiloto'],
            ['3', 'Retardo inaceptable en la captura', 'Masa que anula la sustentación', 'Comunicación insegura con la '
             'computadora'],
            ['4', 'Desempeño pobre ante interferencias', 'Consumo desproporcionado', 'Conexión inestable'],
            ['5', 'Desempeño regular, con desventajas físicas', 'Rendimiento medio por masa térmica', 'Requiere '
             'adaptaciones físicas excesivas'],
            ['6', 'Aceptable, sensible al ruido lumínico', 'Aceptable, con pocos cuadros por segundo', 'Une procesamiento '
             'y control en una placa saturable'],
            ['7', 'Bueno, con limitaciones menores', 'Bueno, con compromisos de energía', 'Compatible, sin soporte nativo '
             'para emergencias'],
            ['8', 'Muy bueno, captura estable y baja masa', 'Buen equilibrio entre cómputo y masa', 'Control externo '
             'seguro'],
            ['9', 'Excelente, alta inmunidad a la luz solar', 'Inferencia ágil con bajo consumo', 'Comunicación '
             'bidireccional excelente'],
            ['10', 'Percepción rápida, estable y redundante', 'Integración completa y alimentación aislada', 'Control total '
             'con rutinas de fallo seguro estándar'],
        ]

INVENTARIO = [['Componente', 'Referencia', 'Cantidad', 'Función'],
               ['Chasis', 'ZD550, fibra de carbono, configuración X', '1', 'Estructura'],
               ['Motores', 'Brushless 2212-920 KV', '4', 'Propulsión'],
               ['Variadores', '40 A, tipo OPTO (sin BEC)', '4', 'Control de los motores'],
               ['Hélices', '[FALTA: referencia]', '4', 'Propulsión'],
               ['Controladora de vuelo', 'Pixhawk 2.4.8 con ArduCopter 4.7.0', '1', 'Estabilización y modos de vuelo'],
               ['Módulo de potencia', 'Power Module PM05-V1.0', '1', 'Alimenta la Pixhawk y mide tensión y corriente'],
               ['Placa de distribución', 'PDB', '1', 'Reparte la energía a los variadores'],
               ['Batería', 'LiPo 4S, 6200 mAh, 14.8 V, 77 Wh', '1', 'Fuente de energía'],
               ['Convertidor', 'DC-DC buck, salida 12.02 V', '1', 'Alimentación de la Jetson'],
               ['Computadora de a bordo', 'NVIDIA Jetson Orin Nano', '1', 'Percepción y decisión'],
               ['Cámara', 'Web USB Sonix, 640×480, HFOV 38.9°', '1', 'Video frontal'],
               ['LiDAR', 'Benewake TF03 (UART)', '1', 'Distancia frontal'],
               ['Adaptador', 'USB-TTL Prolific PL2303', '1', 'Conexión del LiDAR'],
               ['Estabilizador', 'BaseCam SimpleBGC, 2 ejes', '1', 'Estabiliza la cámara y el LiDAR'],
               ['GPS', 'Módulo GPS de la Pixhawk', '1', 'Posición para el modo GUIDED'],
               ['Radiocontrol', 'Futaba T14SG', '1', 'Mando del piloto'],
               ['Receptor', 'Corona con codificador PPM', '1', 'Recepción del radiocontrol'],
               ['Cable de datos', 'DF13 de TELEM2 a conector Dupont (sin 5 V)', '1', 'Enlace MAVLink con la Jetson']]

PARAM_ARDUPILOT = [['Parámetro', 'Valor', 'Motivo'],
              ['SERIAL2_PROTOCOL', '2 (MAVLink 2)', 'TELEM2 es el enlace con la Jetson'],
              ['SERIAL2_BAUD', '115 (115200)', 'A 460800 y 921600 la Pixhawk no entiende a la Jetson'],
              ['BRD_SER2_RTSCTS', '0', 'El cable solo lleva TX, RX y GND'],
              ['FLTMODE_CH', '5', 'El interruptor de tres posiciones de CH5 elige el modo'],
              ['FLTMODE1 / 4 / 6', '[FALTA: modos finales]', 'Ver 2.2.3'],
              ['RC8_OPTION', '31', 'CH8 = parada de emergencia de los motores'],
              ['FS_THR_ENABLE', '1', 'Pérdida de radio: regreso al despegue (RTL)'],
              ['BATT_FS_LOW_ACT', '2', 'Batería baja: RTL'],
              ['BATT_LOW_VOLT / BATT_CRT_VOLT', '13.5 V / 13.2 V', 'Evitan activaciones por caída de tensión bajo carga'],
              ['MNT1_TYPE', '0', 'Sin librería de gimbal, para no duplicar la estabilización'],
              ['SERVO9_FUNCTION', '0', 'AUX1 libre: la maneja la Jetson con DO_SET_SERVO'],
              ['SERVO9_MIN / TRIM / MAX', '1000 / 1500 / 2000', 'Equivale a ±45° del estabilizador'],
              ['BRD_SAFETY_MASK', '16368', 'Salidas 5 a 14 activas con el seguro puesto (banco)'],
              ['LOIT_SPEED', '400 (4 m/s)', 'Velocidad máxima segura con personas (2.3.2)'],
              ['LOIT_BRK_ACCEL', '[FALTA: valor leído en la Pixhawk]', 'Aceleración de frenado usada en d_safe'],
              ['GUID_TIMEOUT', '[FALTA: valor leído en la Pixhawk]', 'Frenado automático si la Jetson deja de enviar']]

PARAM_SOFTWARE = [['Parámetro del software', 'Valor', 'Dónde se justifica'],
              ['Umbral de probabilidad del clasificador', '0.7', '2.3.2'],
              ['Cuadros seguidos para intervenir', '2', '2.3.2'],
              ['Horizonte de predicción', '3 s', '2.3.2'],
              ['Zona de riesgo de una persona', '2 m', '2.3.2'],
              ['Bloqueo frontal por LiDAR', '3 m con avance', '2.1.8 y 2.3.2'],
              ['Árbitro: autoriza el ascenso', '< 3 m, o < 8 m acercándose a más de 0.4 m/s', '2.3.2'],
              ['Salvaguarda geométrica', 'Paso a < 2 m en < 1.5 s', '2.2.6'],
              ['Altura de vuelo del piloto / altura segura', '2.3 m / 3.30 m', '2.3.2'],
              ['Inclinación del estabilizador', '−5° (1444 µs en AUX1)', '2.2.2'],
              ['d_safe: reacción, frenado, margen, radio', '0.5 s; 2.5 m/s²; 1.5 m; 0.4 m', '2.1.8'],
              ['Tiempo mínimo al choque', '2.5 s', '2.1.8'],
              ['Frecuencia de registro', '10 Hz (CSV de la Jetson)', '2.2.6']]

PROTOCOLO = [['Escenario', '¿Activar?', 'Éxito con el sistema', 'Éxito sin ayuda del operador', 'Vuelo seguro sin el '
                 'sistema', 'Choques con / sin'],
                ['a) Panel, 1 m/s', 'sí', '100 % [96, 100]', '100 %', '0 %', '0 / 2'],
                ['a) Panel, 2 m/s', 'sí', '100 % [96, 100]', '100 %', '0 %', '0 / 0'],
                ['a) Panel, 3 m/s', 'sí', '100 % [96, 100]', '100 %', '0 %', '0 / 0'],
                ['a) Panel, 4 m/s', 'sí', '100 % [96, 100]', '100 %', '0 %', '0 / 0'],
                ['b) Persona quieta, 1.5 m/s', 'sí', '100 % [96, 100]', '100 %', '0 %', '0 / 1'],
                ['b) Persona quieta, 3.0 m/s', 'sí', '100 % [96, 100]', '100 %', '0 %', '0 / 0'],
                ['c) De frente caminando', 'sí', '100 % [96, 100]', '100 %', '0 %', '0 / 99'],
                ['c) De frente corriendo', 'sí', '100 % [96, 100]', '72 % [63, 80]', '0 %', '0 / 98'],
                ['d) Cruza lejos caminando', 'no', '100 % [96, 100]', '100 %', '100 %', '0 / 0'],
                ['d) Cruza lejos corriendo', 'no', '100 % [96, 100]', '100 %', '100 %', '0 / 0'],
                ['e) Estático, viene caminando', 'sí', '100 % [96, 100]', '100 %', '0 %', '0 / 100'],
                ['e) Estático, viene corriendo', 'sí', '100 % [96, 100]', '100 %', '0 %', '0 / 100'],
                ['e) Estático, pasa de lado a 5 m', 'no', '100 % [96, 100]', '100 %', '100 %', '0 / 0']]

MUNDOS = [['Decisor', 'Riesgos no evitados', 'Choques', 'Persona a < 2 m bajo 3.30 m', 'Activaciones innecesarias',
                 'Detenido sin necesidad (s)'],
                ['Sin sistema', '2043', '1681', '1488', '—', '—'],
                ['Reglas', '92 (4.5 %)', '39', '420', '137', '2358'],
                ['IA sola', '62 (3.0 %)', '27', '143', '54', '813'],
                ['IA con reglas', '67 (3.3 %)', '28', '218', '67', '1082']]

DEGRADADAS = [['Condición', 'Reglas: éxito · choques · innecesarias', 'IA con reglas: éxito · choques · innecesarias'],
               ['C0 Nominal', '97.6 % · 0 · 44', '98.3 % · 0 · 30'],
               ['C1 Recall de YOLO 0.85 (sol de frente)', '97.6 % · 0 · 43', '98.4 % · 0 · 28'],
               ['C2 Recall de YOLO 0.70 (desenfoque)', '97.7 % · 0 · 42', '98.3 % · 0 · 30'],
               ['C3 Medio cuerpo visible', '97.1 % · 0 · 52', '97.8 % · 0 · 39'],
               ['C4 Solo torso visible', '97.1 % · 0 · 53', '97.3 % · 0 · 48'],
               ['C5 LiDAR con ruido ×3 y 5 % sin retorno', '97.6 % · 0 · 44', '98.3 % · 0 · 30'],
               ['C6 Latencia total de 200 ms', '97.6 % · 0 · 44', '98.3 % · 0 · 30'],
               ['C7 Latencia total de 300 ms', '97.6 % · 0 · 44', '98.3 % · 0 · 30'],
               ['C8 Viento de cola de 3 m/s con ráfagas', '97.2 % · 0 · 50', '98.3 % · 0 · 30'],
               ['C9 Viento de cola de 5 m/s con ráfagas', '97.2 % · 0 · 51', '98.1 % · 0 · 33'],
               ['C10 Combinada', '96.8 % · 0 · 57', '98.0 % · 0 · 35'],
               ['C11 Recall de YOLO 0.40', '97.4 % · 0 · 45', '97.4 % · 0 · 46'],
               ['C12 Solo cabeza y hombros', '96.9 % · 1 · 52', '96.5 % · 1 · 61'],
               ['C13 Latencia total de 500 ms', '97.6 % · 0 · 44', '98.3 % · 0 · 30']]

VELOCIDADES = [['Condición', 'Panel fijo', 'Persona quieta', 'Persona que corre hacia el dron'],
               ['C0 Nominal', '11', '4', '10'], ['C6 Latencia de 200 ms', '11', '4', '9'],
               ['C7 Latencia de 300 ms', '10', '4', '7'], ['C10 Combinada', '11', '4', '8'],
               ['C11 Recall 0.40', '11', '4', '7'], ['C12 Solo cabeza y hombros', '11', '4', '0'],
               ['C13 Latencia de 500 ms', '10', '4', '5']]

CLASIFICADOR = [['Concepto', 'Valor'], ['Arquitectura', 'MLP 32-16, ReLU, 15 entradas, 1 salida'],
                ['Cuadros de entrenamiento', '2 551 725 (13 % con riesgo)'], ['Cuadros de validación', '499 021'],
                ['Cuadros de prueba', '533 085 (12 % con riesgo)'], ['Umbral y persistencia', '0.7 y 2 cuadros'],
                ['Área bajo la curva ROC', '0.974'], ['Precisión media', '0.914'],
                ['Exhaustividad por cuadro', '74.4 %'], ['Precisión', '97.0 %'], ['Falsos positivos', '0.3 %']]

CONFUSION = [['', 'Predice CONTINUAR', 'Predice DETENER'], ['Sin riesgo real', '470 330', '1 420'],
             ['Con riesgo real', '15 716', '45 619']]

MODULOS = [['Archivo', 'Qué hace'],
           ['jetson/config.py', 'Parámetros: puertos, campo de visión, umbrales'],
           ['jetson/percepcion.py', 'Cámara y YOLO26n en TensorRT con seguimiento'],
           ['jetson/lidar_tf.py', 'Lectura y validación de las tramas del TF03'],
           ['jetson/gimbal_basecam.py', 'Telemetría del estabilizador BaseCam'],
           ['jetson/sensores.py, jetson/comun.py', 'Fusión de sensores y utilidades'],
           ['jetson/registro_minimo.py', 'Registro sincronizado de cámara, LiDAR y Pixhawk'],
           ['jetson/intervencion_banco.py', 'Intervención por MAVLink en banco: GUIDED, subida y retoma del piloto'],
           ['simulacion/minimo_tesis/decisor_ia.py', 'Clasificador de riesgo y su evaluación con NumPy'],
           ['simulacion/minimo_tesis/sistema.py', 'Lógica mínima y envolvente de reglas de seguridad'],
           ['simulacion/minimo_tesis/protocolo_comite.py', 'Escenarios del protocolo y métricas']]
