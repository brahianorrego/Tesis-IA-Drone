"""Estado del arte, marco teórico, marco conceptual, marco normativo y metodología."""
import copy

from motor import AMARILLO, ROJO, TURQ, ROSA, VERDE


def aplicar(M, reescribir, mover, DIAG):
    P = M.P
    # ---------------- 1.5 estado del arte: los diez antecedentes, con figuras y una tabla comparativa
    import io
    import os
    from PIL import Image, ImageDraw, ImageFont
    from docx.oxml.ns import qn
    FOTOS = os.environ.get('FOTOS', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fotos'))
    os.makedirs(FOTOS, exist_ok=True)

    def blob(par):
        rid = par._p.xpath('.//a:blip')[0].get(qn('r:embed'))
        return M.d.part.related_parts[rid].blob

    def componer(partes, nombre, alto=640):
        """Une varias imágenes en una fila con rótulos (a), (b)... y devuelve la ruta."""
        ims = []
        for par, _ in partes:
            im = Image.open(io.BytesIO(blob(par))).convert('RGB')
            ims.append(im.resize((int(im.width * alto / im.height), alto)))
        sep = 24
        W = sum(i.width for i in ims) + sep * (len(ims) - 1)
        out = Image.new('RGB', (W, alto), 'white')
        d = ImageDraw.Draw(out)
        fuente = ImageFont.truetype('/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf', 44)
        x = 0
        for k, im in enumerate(ims):
            out.paste(im, (x, 0))
            if len(ims) > 1:
                d.rectangle([x, 0, x + 70, 62], fill='white')
                d.text((x + 8, 4), '(%s)' % 'abcdef'[k], font=fuente, fill='black')
            x += im.width + sep
        ruta = os.path.join(FOTOS, nombre)
        out.save(ruta)
        return ruta

    def nota_de(indices):
        t = [P[i].text.strip() for i in indices]
        t = [x[5:].strip() if x.startswith('Nota.') else x for x in t]
        if len(t) == 1:
            return 'Nota. ' + t[0]
        return 'Nota. ' + ' '.join('(%s) %s' % ('abcdef'[k], x) for k, x in enumerate(t))

    figs = [('ant1', 'Trabajos internacionales sobre vuelo con visión por computador', 'ant_fig1.png',
             [(P[212], 'a'), (P[216], 'b')], [213, 217]),
            ('ant2', 'Clasificación de los trabajos y de los métodos de detección y evasión de obstáculos en UAV',
             'ant_fig2.png', [(P[221], 'a'), (P[225], 'b')], [222, 226]),
            ('ant3', 'Trabajos nacionales sobre visión por computador y evasión en vehículos aéreos',
             'ant_fig3.png', [(P[229], 'a'), (P[233], 'b'), (P[241], 'c')], [230, 234, 242]),
            ('ant4', 'Trabajos locales y departamentales sobre vehículos aéreos y visión artificial',
             'ant_fig4.png', [(P[237], 'a'), (P[245], 'b')], [238, 246])]
    for i in range(210, 249):
        M.marcar(P[i])
    H3 = P[281]
    q = P[248]

    def figura_ant(q, k):
        clave, titulo, archivo, partes, notas = next(f for f in figs if f[0] == k)
        ruta = componer(partes, archivo)
        cap = M.rotulo(q, 'Figura', clave, titulo)
        fig = M.figura(cap, ruta, ancho_cm=15.5, alto_max=9.5)
        return M.nota(fig, nota_de(notas))

    q = M.parrafo(q, '1.5.1 Antecedentes internacionales', AMARILLO, ppr_de=H3)
    q = M.parrafo(q, 'Falanga et al. (2017) hicieron pasar un cuadricóptero por aberturas estrechas con sensado y '
                     'procesamiento a bordo y sin GNSS, y mostraron que la latencia del procesamiento limita la seguridad '
                     'de una maniobra exigente. Valenti et al. (2018) propusieron una arquitectura modular, con módulos '
                     'separados de percepción, localización y evasión, para navegar con visión en entornos congestionados '
                     'y sin GPS; ambos trabajos se ilustran en la {F:ant1}. Dos revisiones ubican el problema: '
                     'Vera-Yanez et al. (2023) revisaron 85 publicaciones sobre detección visual de obstáculos y '
                     'encontraron que la mayoría se valida en simulación y muy pocas en vehículos reales, y Merei et al. '
                     '(2025) concluyen que la evasión sigue siendo uno de los problemas centrales de los UAV; la {F:ant2} '
                     'resume la clasificación de cada una.', AMARILLO)
    q = figura_ant(q, 'ant1')
    q = figura_ant(q, 'ant2')
    q = M.parrafo(q, '1.5.2 Antecedentes nacionales', AMARILLO, ppr_de=H3)
    q = M.parrafo(q, 'En Colombia, Gallo Sanabria et al. (2020) desarrollaron un seguimiento de trayectoria para un UAV '
                     'con visión artificial, y Bohórquez Caro (2021) construyó un sistema embebido de visión que detecta '
                     'y sigue un objetivo móvil desde un UAV con ROS. En Bogotá, Avilés Correa y Garzón Bernal [FALTA: '
                     'año, tomado del repositorio de la Fundación Universitaria Los Libertadores] implementaron un '
                     'sistema de detección y evasión de obstáculos de bajo costo para drones de ala fija, con cámara, '
                     'LiDAR y sensor infrarrojo: es el antecedente más cercano, aunque su plataforma es de ala fija. La '
                     '{F:ant3} muestra el esquema del primer trabajo y las portadas de los otros dos.', AMARILLO)
    q = figura_ant(q, 'ant3')
    q = M.parrafo(q, '1.5.3 Antecedentes locales', AMARILLO, ppr_de=H3)
    q = M.parrafo(q, 'En Madrid (Cundinamarca), León Mondragón y Rojas Díaz [FALTA: año] usaron aeronaves no tripuladas y '
                     'fotogrametría digital para identificar zonas de riesgo, sin tratar la evasión de obstáculos. En la '
                     'Universidad de San Buenaventura, Córdoba Velásquez y Ruiz Rincón (2023) usaron YOLOv5 y Python para '
                     'detectar personas en tiempo real en un dispositivo auditivo que guía en interiores a personas con '
                     'discapacidad visual, y Castro Gutiérrez y Ortega Hernández (2017) desarrollaron una interfaz '
                     'cerebro-computador para controlar la elevación y el avance de un cuadricóptero. El primero no es una '
                     'aplicación aérea y el segundo no usa visión por computador. La {F:ant4} muestra las portadas de los '
                     'dos primeros.', AMARILLO)
    q = figura_ant(q, 'ant4')
    q = M.parrafo(q, '1.5.4 Un tema poco estudiado', AMARILLO, ppr_de=H3)
    q = M.parrafo(q, 'Los antecedentes resuelven partes del problema por separado: detectar personas con YOLO, seguir un '
                     'objetivo desde un UAV, evadir obstáculos con varios sensores en un ala fija o controlar un '
                     'cuadricóptero sin visión. Entre los trabajos revisados, ninguno junta en un cuadricóptero la '
                     'detección de personas con un modelo preentrenado, un LiDAR de proximidad, una decisión aprendida '
                     'acotada por reglas de seguridad y una validación repetible en exteriores; la {T:tA1} compara los '
                     'diez. Las revisiones apuntan en el mismo sentido: pocas propuestas se prueban en vehículos reales '
                     '(Vera-Yanez et al., 2023) y la evasión sigue sin resolverse del todo (Merei et al., 2025). El tema '
                     'está poco estudiado en el nivel que aborda este trabajo, la integración y la validación en una '
                     'aeronave real, y ahí se ubica su aporte. [REVISAR: documentar la búsqueda hecha (bases de datos, '
                     'palabras clave y años) para respaldar que el tema está poco estudiado]', AMARILLO)
    filas_ant = [['Ámbito', 'Trabajo', 'Qué hace', 'Relación con este trabajo'],
                 ['Internacional', 'Falanga et al. (2017)', 'Vuelo de un cuadricóptero por aberturas estrechas, con sensado y cómputo a bordo y sin GNSS', 'La latencia del procesamiento condiciona la seguridad'],
                 ['Internacional', 'Valenti et al. (2018)', 'Arquitectura modular de percepción, localización y evasión sin GPS', 'Misma organización en módulos con interfaces definidas'],
                 ['Internacional', 'Vera-Yanez et al. (2023)', 'Revisión de 85 trabajos de detección visual de obstáculos', 'La mayoría se valida en simulación: justifica probar en una aeronave real'],
                 ['Internacional', 'Merei et al. (2025)', 'Revisión de métodos de detección y evasión en UAV', 'La evasión sigue abierta; pide equilibrar detección, complejidad y viabilidad a bordo'],
                 ['Nacional', 'Gallo Sanabria et al. (2020)', 'Seguimiento de trayectoria de un UAV con visión artificial', 'Cámara que genera acciones de control; sigue una ruta, no evita obstáculos'],
                 ['Nacional', 'Bohórquez Caro (2021)', 'Detección y seguimiento de un objetivo móvil desde un UAV con visión embebida y ROS', 'Integra visión embebida y arquitectura de vuelo; no trata la evasión'],
                 ['Nacional', 'Avilés Correa y Garzón Bernal', 'Detección y evasión de obstáculos de bajo costo con cámara, LiDAR e infrarrojo', 'El más cercano; plataforma de ala fija'],
                 ['Departamental', 'León Mondragón y Rojas Díaz', 'UAS y fotogrametría para identificar zonas de riesgo en Madrid (Cundinamarca)', 'Uso de UAS en un escenario real; no trata la evasión'],
                 ['Local', 'Córdoba Velásquez y Ruiz Rincón (2023)', 'Detección de personas con YOLOv5 en un dispositivo auditivo para interiores', 'Detecta personas en tiempo real; no es una aeronave'],
                 ['Local', 'Castro Gutiérrez y Ortega Hernández (2017)', 'Control de elevación y avance de un cuadricóptero con una interfaz cerebro-computador', 'Experiencia institucional con el cuadricóptero; sin visión por computador']]
    cap = M.rotulo(q, 'Tabla', 'tA1', 'Comparación de los diez antecedentes con este trabajo')
    t_ant = M.tabla(cap, filas_ant, [2.3, 3.6, 5.2, 4.4])
    q = M.nota(t_ant, 'Nota. Elaboración propia a partir de las fuentes citadas en 1.5.1 a 1.5.3. [REVISAR: confirmar cada '
                      'fila leyendo la fuente completa antes de entregar]')

    # ---------------- 1.6 marco teórico (mínimo; las ecuaciones esenciales se conservan, el detalle va al Anexo H)
    reescribir([251], [
        'YOLO (*You Only Look Once*) detecta objetos en tiempo real con una sola evaluación de la red, que entrega cajas '
        'delimitadoras y probabilidades de clase (Redmon et al., 2016). Este trabajo usa un modelo preentrenado con COCO, '
        'que incluye la clase *person* (Lin et al., 2014); la versión YOLO26n corre en la Jetson con TensorRT '
        '(Ultralytics, s. f.). El alto, el ancho, el área y el ángulo de la caja que entrega el detector son entradas del '
        'clasificador de riesgo de 1.6.5.'])
    M.marcar(P[252])
    reescribir([253], ['Formalmente, una detección es una caja delimitadora asociada a una confianza:'])
    for i in range(256, 266):
        M.marcar(P[i])
    M.marcar_ecuacion(P[259])
    M.marcar_ecuacion(P[261])
    M.marcar_ecuacion(P[264])
    M.reemplazar(P[266], '1.6.3', '1.6.2')
    reescribir([267], [
        'El LiDAR mide la distancia frontal por tiempo de vuelo (*Time of Flight*, ToF): emite un pulso de luz infrarroja '
        'y calcula la distancia a partir del tiempo que tarda en volver (Brand, 2021):'])
    M.reemplazar(P[269], 'Esta relación constituye el fundamento físico de la medición de distancia utilizada en el '
                         'proyecto de grado. (Analog Devices, 2021).', '')
    reescribir([270], [
        'En este sistema el LiDAR no reconstruye el entorno: entrega una sola distancia frontal, suficiente para activar '
        'una respuesta de seguridad. La condición de riesgo frente a un obstáculo se expresa con un umbral:'])
    M.reemplazar(P[272], 'Esta formulación es coherente con el alcance del proyecto, ya que no pretende realizar '
                         'planeación tridimensional ni mapeo completo del entorno, sino detectar una condición frontal de '
                         'peligro y activar una maniobra básica de seguridad.', 'El valor de d_safe y su origen se '
                         'explican en 2.1.10.')
    M.reemplazar(P[273], '1.6.4', '1.6.3')
    reescribir([274], [
        'La lógica del sistema es discreta: vigila la detección y la proximidad y no incluye ninguna ley de navegación '
        'autónoma. Se puede ver como un sistema de eventos discretos: ciertas condiciones de entrada producen '
        'transiciones entre estados de operación.'])
    reescribir([278], [
        'En el modo experimental, la lógica de seguridad tiene prioridad sobre el comando de avance cuando hay riesgo de '
        'colisión. Como el protocolo limita la prueba al avance frontal y a la evasión vertical, la respuesta automática '
        'es una secuencia de detención y ascenso:'])
    reescribir([280], [
        'La expresión no modela un controlador de vuelo; solo formaliza el criterio de decisión. Durante la maniobra, la '
        'estabilización la siguen haciendo los controladores de ArduPilot.'])
    M.reemplazar(P[281], '1.6.5', '1.6.4')
    reescribir([282], [
        'Una detección correcta no sirve si la orden llega tarde. El tiempo total del ciclo se descompone en captura, '
        'inferencia, decisión, comunicación y ejecución:'])
    M.marcar(P[284])
    q = reescribir([285], [
        'Separar el ciclo en etapas permite ver cuál limita la respuesta. La latencia pesa más cuando la decisión la toma '
        'una computadora externa al autopiloto: en ArduPilot, la computadora de a bordo envía consignas en el modo GUIDED '
        'por MAVLink y, si dejan de llegar durante el tiempo fijado por GUID_TIMEOUT, la controladora detiene el '
        'vehículo por su cuenta (ArduPilot, s. f.-a).'])
    q = M.parrafo(q, '1.6.5 Clasificador de riesgo con un perceptrón multicapa', AMARILLO, ppr_de=P[281])
    for t in [
        'Un perceptrón multicapa (MLP) es una red neuronal de capas totalmente conectadas que aprende una función a '
        'partir de ejemplos etiquetados, ajustando sus pesos por retropropagación del error (Rumelhart et al., 1986). '
        'Aquí se usa como clasificador: recibe un vector x con quince medidas de los sensores y entrega la probabilidad '
        'de que haya riesgo en los próximos segundos:',
        'p = σ( W₃ · ReLU( W₂ · ReLU( W₁ · x + b₁ ) + b₂ ) + b₃ )                (9)',
        'donde W₁, W₂ y W₃ son las matrices de pesos de las capas (32 y 16 neuronas ocultas), b₁, b₂ y b₃ los sesgos, '
        'ReLU(z) = máx(0, z) la función de activación y σ la función logística. La decisión discreta usa un umbral τ y '
        'una persistencia de k cuadros:',
        'intervenir(t) = 1  si  p(t − j) ≥ τ  para j = 0, …, k − 1;  0 en otro caso                (10)',
        'Con esta formulación, la condición de riesgo deja de ser un único umbral de distancia: el clasificador combina '
        'la distancia, el tamaño de la caja, la velocidad de acercamiento y la persistencia de la detección, y las '
        'reglas de la ecuación (6) se mantienen como una envolvente que la red no puede saltar. La implementación usa '
        'la biblioteca scikit-learn (Pedregosa et al., 2011).',
        'Para mayor información, consulte el Anexo H.']:
        q = M.parrafo(q, t, AMARILLO)
    M.renumerar_ecuaciones([(268, '(8)', '(4)'), (271, '(9)', '(5)'), (276, '(10)', '(6)'), (279, '(11)', '(7)'),
                            (283, '(12)', '(8)')])
    M.parrafo(q, '[REVISAR: se quitó la subsección de variables geométricas (centroide, área y región de observación, '
                 'ecuaciones 4 a 7), que pasó al Anexo H, y se renumeraron las ecuaciones siguientes]', TURQ)

    # ---------------- 1.7 marco conceptual (tres definiciones breves; el detalle va al Anexo H)
    reescribir([288], [
        'Un vehículo aéreo no tripulado es una aeronave sin piloto a bordo, guiada por un operador o por un sistema '
        'automático. En este trabajo la plataforma es un cuadricóptero experimental operado al aire libre en un entorno '
        'controlado, donde las condiciones de ensayo se pueden definir y repetir.'])
    reescribir([289], [
        'Por operación en exteriores se entiende el ensayo en una zona delimitada, señalizada e inspeccionada antes de '
        'volar, con obstáculos tipo panel, una trayectoria de avance frontal y márgenes de seguridad fijados de antemano. '
        'En cada jornada se registran el viento y la iluminación.'])
    for i in (290, 291, 292, 295, 296, 297, 298, 302, 303, 304, 305, 306, 307, 308, 309, 310, 311, 312, 313, 314, 315,
              316, 317, 318, 319, 321, 322, 323):
        M.marcar(P[i])
    M.reemplazar(P[293], '(Pixhawk)', 'y comunicación MAVLink')
    reescribir([294], [
        'La Pixhawk se encarga del control de bajo nivel: estabilización, armado, modos de vuelo y rutinas de fallo '
        'seguro, con el firmware ArduCopter. No detecta personas ni decide la maniobra: recibe las órdenes del módulo de '
        'decisión y mantiene la aeronave estable mientras las ejecuta. Con la computadora de a bordo se comunica por '
        'MAVLink, un protocolo de mensajes por el que viajan el estado de la aeronave (modo, armado, altura y velocidad) '
        'y las órdenes de la maniobra de seguridad.'])
    M.marcar(P[299])
    M.reemplazar(P[300], '1.7.4 Percepción visual', '1.7.3 Percepción visual y evasión básica')
    reescribir([301], [
        'La percepción visual convierte las imágenes de la cámara en información para decidir. Aquí se limita a detectar '
        'personas y a estimar su posición y su cercanía aproximada dentro de la imagen.'])
    q = reescribir([320], [
        'La evasión básica es una respuesta automática de seguridad ante una condición de riesgo en la trayectoria de '
        'avance: detener el avance y ascender verticalmente hasta una altura segura fijada de antemano. Es una acción '
        'predefinida, y no una navegación autónoma ni una planeación libre de trayectorias. La {F:estados} muestra la '
        'secuencia de estados de la maniobra.'])
    q = M.parrafo(q, 'Para mayor información, consulte el Anexo H.', AMARILLO)

    # ---------------- 1.8 marco normativo (tres subsecciones; el detalle va al Anexo I)
    M.reemplazar(P[325], '1.8.1 Referente internacional general para aeronaves sin piloto',
                 '1.8.1 Marco internacional y colombiano')
    reescribir([326], [
        'El Convenio sobre Aviación Civil Internacional establece en su artículo 8 que una aeronave capaz de volar sin '
        'piloto no puede hacerlo sobre el territorio de un Estado contratante sin autorización especial, y que su vuelo '
        'debe controlarse para no poner en peligro a otras aeronaves (Organización de Aviación Civil Internacional '
        '[OACI], [FALTA: año de la edición consultada]).'])
    for i in (327, 329, 330, 331):
        M.marcar(P[i])
    reescribir([328], [
        'En Colombia, la operación de aeronaves no tripuladas se rige por el RAC 100 (Unidad Administrativa Especial de '
        'Aeronáutica Civil, 2023). Los ensayos son académicos y no comerciales, así que se toma como guía de seguridad: '
        'vuelo dentro de la línea de vista del piloto (VLOS), zona delimitada y señalizada, consulta previa del Visor '
        'Geográfico UAS y ningún sobrevuelo de grupos de personas. Las circulares 100-MAUT-5.0-22-010-CI (registro de '
        'sistemas UAS) y 100-MAUT-5.0-22-009-CI (certificado de idoneidad del piloto) aplican porque los ensayos son al '
        'aire libre. [FALTA: número de registro del cuadricóptero y certificado de idoneidad del piloto, o la '
        'indicación de que están en trámite]'])
    M.marcar(P[332])
    M.reemplazar(P[333], '1.8.4 Seguridad y salud en el trabajo durante los ensayos', '1.8.2 Seguridad y salud en el trabajo')
    reescribir([334], [
        'El Decreto 1072 de 2015 exige identificar peligros, valorar riesgos y definir controles en el trabajo '
        '(Ministerio del Trabajo, 2015). Por eso cada ensayo se planea con zona delimitada, inspección previa de la '
        'aeronave, piloto de seguridad y criterios para interrumpirlo; la lista de verificación está en el apartado 2.3.5.'])
    M.marcar(P[335])
    M.reemplazar(P[336], '1.8.5 Protección de datos personales e imagen', '1.8.3 Protección de datos personales e imagen')
    reescribir([337], [
        'Como el sistema detecta personas en video y los ensayos se graban, aplica la Ley Estatutaria 1581 de 2012 '
        '(Congreso de la República de Colombia, 2012): todo video con una persona identificable se maneja con finalidad '
        'académica, consentimiento previo y acceso restringido. El formato de consentimiento está en el Anexo G.'])
    M.marcar(P[338])
    M.parrafo(P[338], 'Para mayor información, consulte el Anexo I.', AMARILLO)

    # ---------------- 1.9 metodología (mismo contenido, redacción más directa)
    reescribir([341], [
        'La investigación tiene un enfoque mixto y un diseño experimental, porque combina análisis cuantitativo y '
        'cualitativo en una misma ruta de trabajo. La parte cuantitativa corresponde a las métricas que registra el '
        'sistema: latencia de respuesta, activaciones de evasión, tasa de éxito, eventos de riesgo e intervenciones del '
        'operador. La parte cualitativa corresponde a la observación técnica del comportamiento del cuadricóptero '
        'durante las pruebas y al análisis de cómo se integran percepción, decisión y control. El enfoque mixto se '
        'justifica porque no basta con saber cuánto responde el sistema; también interesa cómo responde y en qué '
        'condiciones lo hace con seguridad.'])
    reescribir([342], [
        'La investigación es aplicada, porque resuelve un problema concreto de integración tecnológica en un '
        'cuadricóptero real, y tiene un alcance descriptivo-experimental: documenta el comportamiento del sistema durante '
        'los ensayos y evalúa su desempeño en condiciones controladas. La parte experimental se concreta en un entorno '
        'exterior controlado, una trayectoria de avance frontal, una maniobra de evasión predefinida y un protocolo de '
        'ensayos repetibles.'])
    reescribir([344], [
        'El trabajo se organiza en tres fases secuenciales: la definición de la arquitectura operativa, la integración '
        'funcional de los módulos de percepción, decisión y control en el cuadricóptero, y la validación experimental del '
        'protocolo de evasión en un entorno exterior controlado. Cada fase entrega los insumos de la siguiente y responde '
        'a uno de los objetivos específicos.'])
    reescribir([346], [
        'La primera fase define la arquitectura operativa. Empieza con la revisión de los modelos preentrenados '
        'disponibles para detectar personas en tiempo real y con un filtrado técnico según la capacidad de la '
        'computadora de a bordo, la compatibilidad con la cámara, la robustez frente a la iluminación natural y la '
        'estabilidad de la detección. Las alternativas que pasan el filtro se comparan por estabilidad, velocidad de '
        'inferencia, exigencia computacional y facilidad de implementación, con apoyo en documentación técnica, '
        'literatura especializada, repositorios de desarrollo y pruebas iniciales.'])
    reescribir([347], [
        'Con ese análisis se selecciona el modelo de detección y se define la relación funcional entre la cámara '
        'frontal, el modelo, la computadora de a bordo, el LiDAR de proximidad y la controladora de vuelo, indicando qué '
        'componente cumple cada función en el ciclo percepción–decisión–control. Las herramientas son la revisión '
        'documental en bases académicas, la documentación oficial de modelos y librerías, y Python; las técnicas, el '
        'filtrado por criterios técnicos y el análisis comparativo. El producto es la arquitectura operativa en un '
        'diagrama de bloques, sustentada en la selección del modelo.'])
    reescribir([349], [
        'La segunda fase integra el sistema en el cuadricóptero aeronavegable. Aquí el interés no es seleccionar '
        'alternativas, sino implementar y verificar que la cámara, la computadora de a bordo, el LiDAR, la controladora '
        'Pixhawk y la lógica de evasión funcionen juntos.'])
    reescribir([350], [
        'Primero se implementa la percepción en la computadora de a bordo: se configura el modelo, se prueba con la '
        'cámara frontal y se revisa la estabilidad de su salida. Luego se incorpora el módulo de decisión, que interpreta '
        'la detección y la lectura del LiDAR para decidir cuándo mantener el avance y cuándo activar la maniobra de '
        'seguridad. Por último se configura el enlace con la controladora, para que la decisión se convierta en una '
        'orden que la aeronave pueda ejecutar.'])
    reescribir([351], [
        'Con la comunicación establecida, se hacen pruebas funcionales controladas para comprobar cuatro condiciones: '
        'que la detección de personas sea consistente, que el LiDAR identifique la proximidad frontal, que la lógica '
        'interprete bien ambas entradas y que la controladora ejecute la maniobra, con prioridad sobre el comando manual '
        'de avance cuando hay riesgo. Las herramientas son Python, la librería del modelo, la computadora de a bordo, la '
        'cámara, el LiDAR, la controladora y el enlace serie; las técnicas, la implementación de código, la verificación '
        'funcional y la observación técnica. El producto es el sistema integrado sobre el que se hace la validación.'])
    reescribir([353], [
        'La tercera fase valida el protocolo de evasión en un entorno exterior controlado, con un protocolo de ensayo '
        'repetible y criterios definidos de seguridad operativa.'])
    reescribir([354], [
        'Primero se prepara el escenario al aire libre: se delimita y señaliza la zona de prueba, se fija la '
        'trayectoria de avance frontal y se definen la ubicación de los paneles, el margen vertical seguro y los límites '
        'de viento e iluminación que permiten hacer un ensayo. También se fijan los criterios de éxito y de fallo: un '
        'ensayo es exitoso si la maniobra automática se ejecuta sin colisión y sin salir de la zona de prueba, y es un '
        'fallo si hay colisión, si el ensayo se interrumpe sin estar previsto o si el operador tiene que intervenir de '
        'forma obligatoria.'])
    reescribir([355], [
        'Después se estructura el protocolo: condiciones de inicio, secuencia de operación, número de repeticiones, '
        'variables registradas y causas de interrupción, para que todas las repeticiones sigan la misma lógica y queden '
        'trazables. Durante los ensayos se registran la activación de la evasión, el tiempo de respuesta, los eventos de '
        'riesgo y las intervenciones del operador, con planillas, listas de verificación, bitácora técnica y video de '
        'apoyo. El análisis es descriptivo y se centra en la tasa de éxito, la activación de la evasión, la latencia, los '
        'eventos de riesgo y la intervención del operador.'])
    reescribir([357], [
        'La información se recoge mediante revisión documental, observación técnica directa y experimentación '
        'controlada. La revisión documental sirve para identificar y comparar modelos de detección y para consultar la '
        'documentación técnica de la arquitectura. La observación técnica se aplica durante la integración y los ensayos, '
        'para registrar cómo responde el sistema ante personas, obstrucciones y maniobras automáticas. La '
        'experimentación controlada se usa en la validación del protocolo, con pruebas repetibles en condiciones '
        'definidas de antemano.'])
    reescribir([358], [
        'Los instrumentos son matrices de búsqueda y filtrado, una bitácora técnica de implementación, una planilla de '
        'registro de ensayos y una lista de verificación previa a cada prueba, con registro audiovisual de apoyo; los '
        'formatos de registro y consentimiento están en el Anexo G. La información se organiza mediante análisis comparativo, análisis descriptivo e '
        'interpretación técnica, para relacionar lo observado con los objetivos de la investigación.'])
    reescribir([360], [
        'La secuencia del trabajo se resume en un diagrama de flujo metodológico ({F:metod}) que muestra las tres '
        'fases, sus productos y la relación entre ellas.'])
    reescribir([361], [
        'El flujo empieza con la definición del enfoque mixto y del diseño experimental. Sigue la fase de arquitectura: '
        'búsqueda de modelos de inteligencia artificial para detectar personas, criterios de filtrado (capacidad de la '
        'computadora de a bordo, cámara y viabilidad para operar al aire libre) y análisis comparativo. Si el modelo '
        'evaluado no es compatible con los requerimientos, se ajustan los criterios y se revisan otras opciones; si lo '
        'es, se consolida la selección del modelo junto con el LiDAR de proximidad.'])
    reescribir([362], [
        'La segunda fase implementa la arquitectura de forma progresiva: programación de la percepción y la decisión en '
        'la computadora de a bordo, y luego comunicación con la Pixhawk y pruebas funcionales. Si la integración no '
        'funciona, el flujo obliga a corregir y ajustar el sistema antes de pasar a los vuelos de prueba.'])
    reescribir([363], [
        'La fase final define el escenario exterior y el protocolo, ejecuta los ensayos, registra los resultados y '
        'analiza las métricas (latencia, activaciones, tasa de éxito, eventos de riesgo e intervención del operador). Si '
        'no se cumplen los criterios de validación, se ajusta el sistema y se repiten las pruebas hasta obtener un '
        'desempeño satisfactorio.'])
    M.claves[P[364]._p] = ('Figura', 'metod')
    M.marcar(P[365])
    fig = M.figura(P[365], f'{DIAG}/10_metodologia.png', ancho_cm=15.5, color=VERDE)
    M.marcar(P[366])
    M.parrafo(fig, '[REVISAR: la figura original mezclaba tipos de letra y decía "Raspberry Pi" y "entorno indoor". '
                   'Se redibujó con la misma letra del documento, en tres columnas, con el mismo contenido de las fases. '
                   'Se quitó la nota "Elaboración propia": la plantilla USB no la exige para figuras propias]', TURQ,
              estilo='Párr.APA')
