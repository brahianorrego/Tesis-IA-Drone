"""Estado del arte, marco teórico, marco conceptual, marco normativo y metodología."""
from motor import AMARILLO, ROJO, TURQ, ROSA, VERDE


def aplicar(M, reescribir, mover, DIAG):
    P = M.P
    for i, k in ((211, 'falanga'), (220, 'vera'), (224, 'merei'), (228, 'gallo')):
        M.claves[P[i]._p] = ('Figura', k)

    # ---------------- 1.5 estado del arte
    reescribir([210], [
        'Falanga et al. (2017) estudiaron el vuelo de un cuadricóptero a través de aberturas estrechas, con sensado y '
        'procesamiento a bordo y sin GNSS. Su trabajo muestra que, aun con recursos limitados, una maniobra exigente es '
        'posible cuando visión, estimación y control están bien integrados, y que la latencia del procesamiento '
        'condiciona la seguridad de la maniobra. La {F:falanga} muestra la secuencia de vuelo analizada.'])
    reescribir([214], [
        'Valenti et al. (2018) propusieron una arquitectura modular para navegar con visión en entornos congestionados y '
        'sin GPS, con módulos separados de percepción, localización y evasión. Lo que interesa aquí es la organización '
        'explícita del flujo de información entre módulos, la misma idea con la que se estructura este sistema: '
        'percepción, decisión y control como bloques con interfaces definidas.'])
    for i in (215, 216, 217):
        M.marcar(P[i])
    reescribir([218], [
        'En una revisión sistemática de 85 publicaciones sobre detección visual de obstáculos para evitar colisiones en '
        'vuelo, Vera-Yanez et al. (2023) encontraron que el campo crece, sobre todo en detección y seguimiento, pero que '
        'la mayoría de las propuestas se validan en simulación y muy pocas en vehículos reales ({F:vera}). Esa brecha '
        'justifica trabajar con una aeronave física y con un protocolo de ensayo verificable.'])
    reescribir([223], [
        'Merei et al. (2025) revisaron los métodos de detección y evasión de obstáculos en UAV y concluyeron que la '
        'evasión sigue siendo uno de los problemas centrales para operar con seguridad, tanto frente a obstáculos '
        'estáticos como dinámicos ({F:merei}). Su revisión ayuda a ubicar este trabajo: las decisiones de diseño deben '
        'equilibrar la capacidad de detección, la complejidad del algoritmo y la posibilidad real de implementarlo a '
        'bordo.'])
    reescribir([227], [
        'En Colombia, Gallo Sanabria et al. (2020) desarrollaron un sistema de seguimiento de trayectoria para un UAV '
        'basado en visión artificial. Aunque su objetivo es seguir una ruta y no evitar obstáculos, el trabajo muestra '
        'cómo la información de una cámara se convierte en acciones de control sobre una plataforma aérea '
        '({F:gallo}).'])
    reescribir([231], [
        'Bohórquez Caro (2021) construyó un sistema embebido de visión por computador que detecta y sigue un objetivo '
        'móvil desde un UAV usando ROS. Es una referencia nacional sobre la integración del procesamiento visual con la '
        'arquitectura de vuelo en hardware embarcado.'])
    for i in (232, 233, 234, 236, 237, 238, 240, 241, 242, 244, 245, 246):
        M.marcar(P[i])
    mover([235], 'A', 'León Mondragón y Rojas Díaz')
    reescribir([239], [
        'En Bogotá, Avilés Correa y Garzón Bernal [FALTA: año, tomado del repositorio de la Fundación Universitaria Los '
        'Libertadores] implementaron un sistema de detección y evasión de obstáculos de bajo costo para drones de ala '
        'fija, con cámara, LiDAR y sensor infrarrojo. Aunque la plataforma es de ala fija, es uno de los antecedentes '
        'más cercanos a este trabajo, porque combina varios sensores con reglas de respuesta para generar señales de '
        'control.'])
    reescribir([243], [
        'En la Universidad de San Buenaventura, Córdoba Velásquez y Ruiz Rincón (2023) usaron YOLOv5 y Python para '
        'detectar personas en tiempo real en un dispositivo auditivo que ayuda a navegar en interiores a personas con '
        'discapacidad visual. No es una aplicación aérea, pero es un antecedente institucional del uso de la detección '
        'de personas en tiempo real integrada con una respuesta del sistema.'])
    mover([247], 'A', 'Castro Gutiérrez y Ortega Hernández')
    reescribir([248], [
        'En conjunto, los antecedentes muestran avances en arquitecturas basadas en visión y en estrategias de detección '
        'y evasión, pero también una distancia entre la demostración del algoritmo, la simulación y la validación en una '
        'plataforma real de alcance académico. Este trabajo se ubica en ese espacio: no busca una navegación autónoma '
        'completa, sino integrar detección de personas, sensado de proximidad y una maniobra básica de evasión en un '
        'cuadricóptero, y probarla en exteriores con un protocolo repetible. Otros dos antecedentes, uno regional y otro '
        'institucional, menos relacionados con el problema, se describen en el Anexo A.'])

    # ---------------- 1.6 marco teórico
    reescribir([251], [
        'La familia YOLO (*You Only Look Once*) es una de las más influyentes en la detección de objetos en tiempo real. '
        'Su planteamiento trata la detección como una regresión desde la imagen completa hacia cajas delimitadoras y '
        'probabilidades de clase, de modo que una sola red localiza y clasifica en una única evaluación (Redmon et al., '
        '2016). Eso la hace adecuada para aplicaciones con restricciones de tiempo.'])
    reescribir([252], [
        'En este trabajo se usa un modelo YOLO preentrenado con COCO (*Common Objects in Context*), un conjunto de datos '
        'de referencia que incluye la clase *person* (Lin et al., 2014). El objetivo no es entrenar un detector, sino '
        'integrar uno disponible en una plataforma real; la versión usada, YOLO26n, se ejecuta en la Jetson con el motor '
        'de inferencia TensorRT (Ultralytics, s. f.).'])
    reescribir([253], ['Formalmente, una detección es una caja delimitadora asociada a una confianza:'])
    reescribir([257], [
        'A partir de la caja se obtienen variables geométricas que describen la posición de la persona en la imagen. Las '
        'más útiles son el centroide y el área.'])
    reescribir([262], [
        'El centroide ubica a la persona dentro del cuadro y el área sirve como medida aproximada de cercanía: cuanto '
        'más cerca está la persona, más grande es la caja. Usar características de la imagen como variables de '
        'realimentación es la base del control servo visual (Chaumette & Hutchinson, 2006). En el sistema implementado, '
        'el alto, el ancho, el área y el ángulo de la caja son entradas del clasificador de riesgo descrito en 1.6.6.'])
    reescribir([265], ['Esta condición descarta las detecciones que caen fuera de la zona de interés del escenario de '
                       'prueba.'])
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
                         'explican en 2.1.8.')
    reescribir([274], [
        'El sistema no se basa en una ley de navegación autónoma, sino en una lógica discreta que vigila la detección y '
        'la proximidad. Se puede ver como un sistema de eventos discretos: ciertas condiciones de entrada producen '
        'transiciones entre estados de operación.'])
    reescribir([278], [
        'En el modo experimental, la lógica de seguridad tiene prioridad sobre el comando de avance cuando hay riesgo de '
        'colisión. Como el protocolo limita la prueba al avance frontal y a la evasión vertical, la respuesta automática '
        'es una secuencia de detención y ascenso:'])
    reescribir([280], [
        'La expresión no modela un controlador de vuelo; solo formaliza el criterio de decisión. Durante la maniobra, la '
        'estabilización la siguen haciendo los controladores de ArduPilot.'])
    reescribir([282], [
        'Una detección correcta no sirve si la orden llega tarde. El tiempo total del ciclo se descompone en captura, '
        'inferencia, decisión, comunicación y ejecución:'])
    reescribir([284], [
        'Separar el ciclo en etapas permite ver cuál limita la respuesta, y justifica el uso de un modelo ligero, de '
        'decisiones simples y de una comunicación directa con la controladora.'])
    q = reescribir([285], [
        'Esta latencia pesa más cuando la decisión la toma una computadora externa al autopiloto. En ArduPilot, la '
        'computadora de a bordo envía consignas en el modo GUIDED por MAVLink y, si dejan de llegar durante el tiempo '
        'fijado por el parámetro GUID_TIMEOUT, la controladora detiene el vehículo por su cuenta (ArduPilot, s. f.-a).'])
    q = M.parrafo(q, '1.6.6 Clasificador de riesgo con un perceptrón multicapa', AMARILLO, ppr_de=P[281])
    for t in [
        'Un perceptrón multicapa (MLP) es una red neuronal de capas totalmente conectadas que aprende una función a '
        'partir de ejemplos etiquetados, ajustando sus pesos por retropropagación del error (Rumelhart et al., 1986). '
        'Aquí se usa como clasificador: recibe un vector x con quince medidas de los sensores y entrega la probabilidad '
        'de que haya riesgo en los próximos segundos:',
        'p = σ( W₃ · ReLU( W₂ · ReLU( W₁ · x + b₁ ) + b₂ ) + b₃ )                (13)',
        'donde W₁, W₂ y W₃ son las matrices de pesos de las capas (32 y 16 neuronas ocultas), b₁, b₂ y b₃ los sesgos, '
        'ReLU(z) = máx(0, z) la función de activación y σ la función logística. La decisión discreta usa un umbral τ y '
        'una persistencia de k cuadros:',
        'intervenir(t) = 1  si  p(t − j) ≥ τ  para j = 0, …, k − 1;  0 en otro caso                (14)',
        'Con esta formulación, la condición de riesgo deja de ser un único umbral de distancia: el clasificador combina '
        'la distancia, el tamaño de la caja, la velocidad de acercamiento y la persistencia de la detección, y las '
        'reglas de la ecuación (10) se mantienen como una envolvente que la red no puede saltar. La implementación usa '
        'la biblioteca scikit-learn (Pedregosa et al., 2011).']:
        q = M.parrafo(q, t, AMARILLO)

    # ---------------- 1.7 marco conceptual
    reescribir([288], [
        'Un vehículo aéreo no tripulado es una aeronave sin piloto a bordo, guiada por un operador o por un sistema '
        'automático. En este trabajo la plataforma es un cuadricóptero experimental operado al aire libre en un entorno '
        'controlado, donde las condiciones de ensayo se pueden definir y repetir.'])
    reescribir([289], [
        'Por operación en exteriores se entiende el ensayo en una zona delimitada, señalizada e inspeccionada antes de '
        'volar, con obstáculos tipo panel, una trayectoria de avance frontal, márgenes de seguridad fijados de antemano '
        'y registro del viento y la iluminación de cada jornada. No se trata de navegación global ni de posicionamiento '
        'autónomo, sino de comprobar si el sistema responde con seguridad ante personas y obstrucciones en una misión '
        'específica.'])
    for i in (290, 291, 292, 295, 296, 297, 302, 303, 304, 305, 306, 307, 308, 309, 310, 311, 312, 313, 314, 315, 316,
              317, 321, 322, 323):
        M.marcar(P[i])
    reescribir([294], [
        'La controladora de vuelo Pixhawk se encarga del control de bajo nivel: estabilización, lectura de sus sensores '
        'internos, armado, modos de vuelo y rutinas de fallo seguro. En este trabajo ejecuta el firmware ArduCopter; no '
        'detecta personas ni decide la maniobra, sino que recibe las órdenes del módulo de decisión y mantiene la '
        'aeronave estable mientras las ejecuta.'])
    reescribir([299], [
        'MAVLink es el protocolo de mensajes con el que la Jetson Orin Nano y la Pixhawk intercambian información. Por '
        'este enlace la computadora recibe el estado de la aeronave (modo, armado, altura y velocidad) y envía las '
        'órdenes de la maniobra de seguridad.'])
    reescribir([301], [
        'La percepción visual es el proceso que convierte las imágenes de la cámara en información para decidir. Aquí '
        'se limita a detectar personas y a estimar su posición y su cercanía aproximada dentro de la imagen; no incluye '
        'el reconocimiento completo del entorno ni la navegación visual.'])
    reescribir([318], ['1.7.5 Evasión básica de obstáculos'])
    reescribir([319], [
        'La evasión básica es una respuesta automática de seguridad ante una condición de riesgo en la trayectoria de '
        'avance. No es navegación autónoma ni planeación libre de trayectorias: es una acción predefinida que se activa '
        'cuando el sistema identifica una proximidad peligrosa.'])
    reescribir([320], [
        'En este trabajo la maniobra se limita a detener el avance y ascender verticalmente hasta una altura segura '
        'fijada de antemano. Esa delimitación separa el proyecto de las propuestas de evasión en varias direcciones o de '
        'navegación autónoma integral. La {F:estados} muestra la secuencia de estados de la maniobra.'])

    # ---------------- 1.8 marco normativo
    reescribir([326], [
        'El Convenio sobre Aviación Civil Internacional establece en su artículo 8 que ninguna aeronave capaz de volar '
        'sin piloto puede hacerlo sobre el territorio de un Estado contratante sin autorización especial de ese Estado, y '
        'que su vuelo debe controlarse para no poner en peligro a otras aeronaves (Organización de Aviación Civil '
        'Internacional [OACI], [FALTA: año de la edición consultada]). Este principio orienta la forma de plantear los '
        'ensayos: bajo control, con medidas de seguridad y con responsables definidos.'])
    reescribir([328], [
        'En Colombia, la operación de aeronaves no tripuladas se rige por el RAC 100, Operación de Sistemas de Aeronaves '
        'no Tripuladas UAS (Unidad Administrativa Especial de Aeronáutica Civil, 2023). Aunque los ensayos de este '
        'trabajo son académicos y no comerciales, el RAC 100 se adopta como referencia para planear una operación '
        'segura.'])
    reescribir([329], [
        'Como los ensayos se hacen al aire libre, antes de cada jornada se verifican las condiciones del espacio aéreo: '
        'su clasificación, la distancia a personas y edificaciones ajenas a la prueba, el límite de altura y la ausencia '
        'de restricciones geográficas, para lo cual se consulta el Visor Geográfico UAS de la Aerocivil. Los vuelos se '
        'hacen siempre dentro de la línea de vista del piloto (VLOS), sin operaciones más allá de ella y sin sobrevolar '
        'grupos de personas.'])
    reescribir([331], [
        'El trabajo no incluye transporte de carga, uso comercial ni navegación autónoma completa. Por eso el RAC 100 se '
        'toma sobre todo como guía de buenas prácticas: control del vehículo, vuelo dentro de la línea de vista, zona '
        'delimitada y señalizada, consulta previa de restricciones, supervisión permanente del piloto y una misión clara '
        'y verificable.'])
    reescribir([332], [
        'La Aerocivil publica además circulares informativas sobre el registro de sistemas UAS (100-MAUT-5.0-22-010-CI) '
        'y sobre el certificado de idoneidad del piloto (100-MAUT-5.0-22-009-CI). Como los ensayos son al aire libre, '
        'estas circulares aplican al registro de la aeronave y a la acreditación del piloto que ejecuta las pruebas. '
        '[FALTA: número de registro del cuadricóptero y certificado de idoneidad del piloto, o la indicación de que están '
        'en trámite]'])
    reescribir([334], [
        'Además del marco aeronáutico, las pruebas con un cuadricóptero implican riesgos para quienes participan. El '
        'Decreto 1072 de 2015 define la seguridad y salud en el trabajo como la disciplina que previene lesiones y '
        'enfermedades causadas por las condiciones de trabajo, y exige identificar peligros, valorar riesgos y definir '
        'controles (Ministerio del Trabajo, 2015).'])
    reescribir([335], [
        'Aplicado a este trabajo, cada ensayo se planea con control preventivo del riesgo: zona delimitada y '
        'señalizada, inspección previa de la aeronave, control del acceso de terceros, revisión del clima antes de '
        'volar, altura y trayectoria definidas, piloto de seguridad, criterios para interrumpir el ensayo y registro de '
        'incidentes. La lista de verificación correspondiente está en el Anexo G.'])
    reescribir([337], [
        'Como el sistema detecta personas en video y los ensayos se graban para analizarlos, aplica la Ley Estatutaria '
        '1581 de 2012, que regula el tratamiento de datos personales en Colombia y protege el derecho de las personas a '
        'conocer, actualizar y rectificar la información recogida sobre ellas (Congreso de la República de Colombia, '
        '2012).'])
    reescribir([338], [
        'Por eso, todo video en el que una persona sea identificable se maneja con finalidad académica, consentimiento '
        'previo, acceso restringido y sin divulgación no autorizada. El formato de consentimiento para los voluntarios '
        'está en el Anexo G.'])

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
        'formatos están en el Anexo G. La información se organiza mediante análisis comparativo, análisis descriptivo e '
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
    fig = M.figura(P[365], f'{DIAG}/05_metodologia_corregida.png', ancho_cm=15.5, color=VERDE)
    M.marcar(P[366])
    M.parrafo(fig, '[REVISAR: la figura original decía "Raspberry Pi" y "entorno indoor". Es el mismo dibujo con esos dos '
                   'textos corregidos. Se quitó la nota "Elaboración propia": la plantilla USB no la exige para figuras '
                   'propias]', TURQ, estilo='Párr.APA')
