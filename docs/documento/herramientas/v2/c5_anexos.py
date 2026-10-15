"""Referencias y anexos A a G."""
import copy
import math
import unicodedata

from docx.oxml.ns import qn
from docx.shared import Pt
from docx.text.paragraph import Paragraph
from docx.text.run import Run

from motor import AMARILLO, ROJO, TURQ, ROSA, VERDE

REFS = [
    'ArduPilot. (s. f.-a). *Copter commands in guided mode*. ArduPilot Dev Documentation. '
    'https://ardupilot.org/dev/docs/copter-commands-in-guided-mode.html',
    'ArduPilot. (s. f.-b). *Guided mode*. ArduPilot Copter Documentation. '
    'https://ardupilot.org/copter/docs/ac2_guidedmode.html',
    'ArduPilot. (s. f.-c). *Loiter mode*. ArduPilot Copter Documentation. '
    'https://ardupilot.org/copter/docs/loiter-mode.html',
    'Avilés Correa, C. L., & Garzón Bernal, J. D. ([FALTA: año]). *Implementación de un sistema de detección y evasión '
    'de obstáculos de bajo costo para drones de ala fija* [Trabajo de grado, Fundación Universitaria Los '
    'Libertadores]. https://repository.libertadores.edu.co/handle/11371/4904',
    'Benewake. (s. f.). *TF03-180 datasheet* (V1.2). https://en.benewake.com/TF03/index.html',
    'Bohórquez Caro, D. (2021). *Sistema de visión por computador embebido para la detección y el seguimiento de '
    'objetivo móvil desde un vehículo aéreo no tripulado (UAV) usando ROS* [FALTA: tipo de trabajo, Escuela Colombiana '
    'de Ingeniería Julio Garavito]. [FALTA: enlace del repositorio]',
    'Brand, T. (2021, 1 de febrero). *Time of flight system for distance measurement and object detection*. Analog '
    'Devices. https://www.analog.com/en/resources/technical-articles/tof-system-for-distance-measurement-and-object-'
    'detection.html',
    'Castro Gutiérrez, [FALTA: iniciales], & Ortega Hernández, [FALTA: iniciales] (2017). *Implementación de una '
    'interfaz cerebro-computador (BCI) que permita controlar el movimiento de elevación y avance durante el vuelo de un '
    'cuadricóptero (dron)* [Trabajo de grado, Universidad de San Buenaventura]. [FALTA: enlace del repositorio]',
    'Chaumette, F., & Hutchinson, S. (2006). Visual servo control, part I: Basic approaches. *IEEE Robotics & '
    'Automation Magazine, 13*(4), 82–90. https://doi.org/10.1109/MRA.2006.250573',
    'Choutri, K., Lagha, M., Meshoul, S., Shaiba, H., Chegrani, A., & Yahiaoui, M. (2024). Vision-based UAV detection '
    'and localization to indoor positioning system. *Sensors, 24*(13), 4121. https://doi.org/10.3390/s24134121',
    'Congreso de la República de Colombia. (2012, 17 de octubre). *Ley Estatutaria 1581 de 2012: Por la cual se dictan '
    'disposiciones generales para la protección de datos personales* (Diario Oficial n.° 48.587). '
    'https://normograma.mintic.gov.co/mintic/compilacion/docs/ley_1581_2012.htm',
    'Córdoba Velásquez, [FALTA: iniciales], & Ruiz Rincón, [FALTA: iniciales] (2023). *Desarrollo de un dispositivo '
    'auditivo de navegación en espacios interiores para personas con discapacidad visual mediante la implementación de '
    'visión artificial* [Trabajo de grado, Universidad de San Buenaventura]. [FALTA: enlace del repositorio]',
    'Falanga, D., Mueggler, E., Faessler, M., & Scaramuzza, D. (2017). Aggressive quadrotor flight through narrow gaps '
    'with onboard sensing and computing using active vision. En *2017 IEEE International Conference on Robotics and '
    'Automation (ICRA)* (pp. 5774–5781). IEEE. https://doi.org/10.1109/ICRA.2017.7989679',
    'Gallo Sanabria, J. D., Mozuca Tamayo, P. A., & Rincón Fonseca, R. I. (2020). Autonomous trajectory following for '
    'an UAV based on computer vision. *Visión Electrónica, 14*(1), 51–56. https://doi.org/10.14483/22484728.15968',
    'Gerencheal, T. A., & Lee, J. H. (2025). Development of a collision avoidance system using multiple distance '
    'sensors for indoor inspection drone. *Applied Sciences, 15*(16), 8791. https://doi.org/10.3390/app15168791',
    'Kurunathan, H., Huang, H., Li, K., Ni, W., & Hossain, E. (2024). Machine learning-aided operations and '
    'communications of unmanned aerial vehicles: A contemporary survey. *IEEE Communications Surveys & Tutorials, '
    '26*(1), 496–533. https://doi.org/10.1109/COMST.2023.3312221',
    'León Mondragón, [FALTA: iniciales], & Rojas Díaz, [FALTA: iniciales] ([FALTA: año]). *Propuesta metodológica para '
    'la identificación de zonas de riesgo, empleando los sistemas de aeronaves no tripuladas (RPAS). Caso de estudio: '
    'Cerro Casablanca, Madrid, Cundinamarca* [Trabajo de grado, Universidad Distrital Francisco José de Caldas]. '
    'https://repository.udistrital.edu.co/items/ded3eb73-8214-44fc-a339-38da67212904',
    'Liang, Q., Wang, Z., Yin, Y., Xiong, W., Zhang, J., & Yang, Z. (2023). Autonomous aerial obstacle avoidance using '
    'LiDAR sensor fusion. *PLOS ONE, 18*(6), e0287177. https://doi.org/10.1371/journal.pone.0287177',
    'Lin, T.-Y., Maire, M., Belongie, S., Bourdev, L., Girshick, R., Hays, J., Perona, P., Ramanan, D., Zitnick, C. L., & '
    'Dollár, P. (2014). Microsoft COCO: Common objects in context. En D. Fleet, T. Pajdla, B. Schiele, & T. Tuytelaars '
    '(Eds.), *Computer Vision – ECCV 2014* (pp. 740–755). Springer. https://doi.org/10.1007/978-3-319-10602-1_48',
    'McNemar, Q. (1947). Note on the sampling error of the difference between correlated proportions or percentages. '
    '*Psychometrika, 12*(2), 153–157. https://doi.org/10.1007/BF02295996',
    'Meisel Roca, A., & Vega Argote, M. (2007). *La estatura de los colombianos: un ensayo de antropometría histórica, '
    '1910-2002*. Banco de la República. [FALTA: serie, número y enlace]',
    'Merei, A., Mcheick, H., Ghaddar, A., & Rebaine, D. (2025). A survey on obstacle detection and avoidance methods '
    'for UAVs. *Drones, 9*(3), 203. https://doi.org/10.3390/drones9030203',
    'Ministerio del Trabajo. (2015, 26 de mayo). *Decreto 1072 de 2015: Por medio del cual se expide el Decreto Único '
    'Reglamentario del Sector Trabajo* (Diario Oficial n.° 49.523). '
    'https://funcionpublica.gov.co/eva/gestornormativo/norma.php?i=72173',
    'Organización de Aviación Civil Internacional. ([FALTA: año de la edición]). *Convenio sobre Aviación Civil '
    'Internacional* (Doc 7300). OACI.',
    'Pedregosa, F., Varoquaux, G., Gramfort, A., Michel, V., Thirion, B., Grisel, O., Blondel, M., Prettenhofer, P., '
    'Weiss, R., Dubourg, V., Vanderplas, J., Passos, A., Cournapeau, D., Brucher, M., Perrot, M., & Duchesnay, É. '
    '(2011). Scikit-learn: Machine learning in Python. *Journal of Machine Learning Research, 12*, 2825–2830. '
    'https://jmlr.org/papers/v12/pedregosa11a.html',
    'Pugh, S. (1991). *Total design: Integrated methods for successful product engineering*. Addison-Wesley.',
    'PX4 Autopilot. (s. f.). *Raspberry Pi companion with Pixhawk*. PX4 Developer Guide. '
    'https://docs.px4.io/main/en/companion_computer/pixhawk_rpi',
    'Redmon, J., Divvala, S., Girshick, R., & Farhadi, A. (2016). You only look once: Unified, real-time object '
    'detection. En *Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition* (pp. 779–788). '
    'https://doi.org/10.1109/CVPR.2016.91',
    'Rumelhart, D. E., Hinton, G. E., & Williams, R. J. (1986). Learning representations by back-propagating errors. '
    '*Nature, 323*(6088), 533–536. https://doi.org/10.1038/323533a0',
    'Ulrich, K. T., & Eppinger, S. D. (2016). *Product design and development* (6.ª ed.). McGraw-Hill Education.',
    'Ultralytics. (s. f.). *Ultralytics YOLO26*. Ultralytics Docs. https://docs.ultralytics.com/models/yolo26/',
    'Unidad Administrativa Especial de Aeronáutica Civil. (2023). *RAC 100: Operación de sistemas de aeronaves no '
    'tripuladas UAS* (Resolución 01983 de 2023). Aerocivil. [FALTA: confirmar la fecha de la resolución y el enlace '
    'oficial]',
    'Valenti, F., Giaquinto, D., Musto, L., Zinelli, A., Bertozzi, M., & Broggi, A. (2018). Enabling computer '
    'vision-based autonomous navigation for unmanned aerial vehicles in cluttered GPS-denied environments. En *2018 21st '
    'International Conference on Intelligent Transportation Systems (ITSC)* (pp. 3886–3891). IEEE. '
    'https://doi.org/10.1109/ITSC.2018.8569695',
    'Vera-Yanez, D., Pereira, A., Rodrigues, N., Molina, J. P., García, A. S., & Fernández-Caballero, A. (2023). '
    'Vision-based flying obstacle detection for avoiding midair collisions: A systematic review. *Journal of Imaging, '
    '9*(10), 194. https://doi.org/10.3390/jimaging9100194',
    'Wilson, E. B. (1927). Probable inference, the law of succession, and statistical inference. *Journal of the '
    'American Statistical Association, 22*(158), 209–212. https://doi.org/10.1080/01621459.1927.10502953',
]


def _clave(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return s


_CAMBIOS_LISTADO = [
    ('Paso 3 del plan mínimo (docs/PLAN_MINIMO_FISICO.md): intervención', 'Paso 3 del plan de pruebas físicas: intervención'),
    ('Reglas (decisiones del arquitecto, 2026-10-11):', 'Reglas de diseño:'),
    ('FASE G · DECISOR IA del mínimo indispensable: la IA', 'DECISOR IA: la IA'),
    ('tal como las escribe CLAUDE.md (regla 5)', 'tal como las fija el diseño (regla 5)'),
    ('(fase G)', ''),
]


def _limpiar_comentario(linea):
    """En los listados impresos se quitan referencias internas del repositorio (solo comentarios, no código)."""
    for viejo, nuevo in _CAMBIOS_LISTADO:
        linea = linea.replace(viejo, nuevo)
    return linea.rstrip() if linea.strip() else linea


def aplicar(M, movidos, REPO):
    P, T = M.P, M.T
    # ---------------- referencias
    viejas = [p for p in P[565:580]]
    for p in viejas:
        M.marcar(p)
    q = viejas[-1]
    q = M.parrafo(q, '[REVISAR: lista rehecha completa y en orden alfabético: se quitaron Ahmed et al. (duplicado de '
                     'Kurunathan, cuya versión correcta es de 2024), Jiang, Lahmeri, Palossi y "GCS failsafe" (no se '
                     'citaban) y se agregaron las 22 fuentes que se citan en el texto y faltaban. Entradas verificadas '
                     'con búsquedas web: probar cada DOI con un clic. La plantilla recomienda manejarlas con Mendeley]',
                  TURQ, estilo='Párr.APA')
    for ref in sorted(REFS, key=_clave):
        q = M.parrafo(q, ref, VERDE, ppr_de=P[566])

    # ---------------- anexos viejos
    for p in P[581:591]:
        M.marcar(p)
    q = M.parrafo(P[590], '[REVISAR: los apartados A.0 a A.3 describían una versión anterior del programa (con paneo del '
                          'cardán y evasión lateral); se reemplazan por los anexos A a G. Según la plantilla, en la tabla '
                          'de contenido solo aparece "Anexos"; los títulos de cada anexo no son títulos de nivel]', TURQ)

    def titulo_anexo(ancla, letra, nombre):
        p = M.parrafo(ancla, '', AMARILLO, estilo='Normal', alineacion=1, salto_pagina=True)
        M.run(p, f'Anexo {letra}. {nombre}', AMARILLO, bold=True)
        M.marcador(p, f'Anexo_{letra}')
        return p

    def sub(ancla, texto):
        p = M.parrafo(ancla, '', AMARILLO, estilo='Normal')
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.keep_with_next = True
        M.run(p, texto, AMARILLO, bold=True)
        return p

    def par(ancla, texto):
        return M.parrafo(ancla, texto, AMARILLO)

    def tab(ancla, etiqueta, titulo, filas, anchos, nota=None, size=9):
        c = M.rotulo_anexo(ancla, etiqueta, titulo)
        t = M.tabla(c, filas, anchos, size=size)
        return M.nota(t, nota) if nota else M.parrafo(t, '', AMARILLO, estilo='Normal')

    def tabla_movida(ancla, clave, etiqueta, titulo, nota=None):
        c = M.rotulo_anexo(ancla, etiqueta, titulo)
        last = c
        for el in movidos[clave]:
            if el.tag == qn('w:tbl'):
                e = copy.deepcopy(el)
                for b in list(e.iter(qn('w:bookmarkStart'))) + list(e.iter(qn('w:bookmarkEnd'))):
                    b.getparent().remove(b)
                for r in e.iter(qn('w:r')):
                    Run(r, None).font.highlight_color = AMARILLO
                last_el = last._p if hasattr(last, '_p') else last
                last_el.addnext(e)
                last = e
        return M.nota(last, nota) if nota else M.parrafo(last, '', AMARILLO, estilo='Normal')

    def figura_movida(ancla, clave, etiqueta, titulo, nota=None):
        c = M.rotulo_anexo(ancla, etiqueta, titulo)
        last = c._p
        for el in movidos[clave]:
            if el.tag == qn('w:p') and el.xpath('.//w:drawing'):
                e = copy.deepcopy(el)
                for b in list(e.iter(qn('w:bookmarkStart'))) + list(e.iter(qn('w:bookmarkEnd'))):
                    b.getparent().remove(b)
                for r in e.iter(qn('w:r')):
                    Run(r, None).font.highlight_color = AMARILLO
                last.addnext(e)
                last = e
        return M.nota(last, nota) if nota else Paragraph(last, M.d._body)

    q = P[590]
    q = M.parrafo(q, '', AMARILLO, estilo='Normal')  # ancla para los anexos

    # ================= Anexo A
    q = titulo_anexo(q, 'A', 'Antecedentes complementarios')
    q = par(q, 'Estos dos antecedentes, uno regional y otro institucional, se citan en el estado del arte (1.5) pero '
               'tienen menos relación directa con el problema del trabajo.')
    q = par(q, 'León Mondragón y Rojas Díaz [FALTA: año] usaron aeronaves no tripuladas y fotogrametría digital para '
               'identificar zonas de riesgo en el cerro Casablanca, en Madrid (Cundinamarca). No tratan la evasión de '
               'obstáculos, pero el trabajo es un antecedente departamental del uso de UAS en un escenario real, con '
               'énfasis en el diseño metodológico y en la recolección ordenada de datos.')
    q = par(q, 'Castro Gutiérrez y Ortega Hernández (2017) desarrollaron en la Universidad de San Buenaventura una '
               'interfaz cerebro-computador para controlar la elevación y el avance de un cuadricóptero. No usan visión '
               'por computador, pero muestran la experiencia previa de la universidad en la integración de sistemas de '
               'control sobre un cuadricóptero.')

    # ================= Anexo B
    q = titulo_anexo(q, 'B', 'Diseño conceptual detallado')
    q = par(q, 'Este anexo reúne las tablas intermedias del diseño conceptual de 2.1: la generación de alternativas, los '
               'juicios de viabilidad, el filtrado, el significado de cada nivel de la escala de calificación, la prueba '
               'de sensibilidad de la escala, la revisión de la selección con datos medidos, el diagrama del concepto del '
               'diseño y la ponderación del despliegue de la función de calidad.')
    q = sub(q, 'B.1 Generación de conceptos')
    q = tabla_movida(q, 'B1', 'Tabla B1', 'Generación de conceptos específicos por función')
    q = sub(q, 'B.2 Juicios de viabilidad')
    q = par(q, 'Cada concepto se calificó en cuatro niveles (alta viabilidad, viabilidad moderada, riesgo medio y riesgo '
               'crítico) según la dificultad de adquirirlo, su desempeño esperado y su flexibilidad, teniendo en cuenta '
               'la masa, el consumo eléctrico, el ruido y la exposición al clima.')
    q = tabla_movida(q, 'B2', 'Tabla B2', 'Juicios de viabilidad de los conceptos por subfunción',
                     'Nota. El juicio expresa el grado de viabilidad y la razón técnica que lo sustenta.')
    q = sub(q, 'B.3 Filtrado de conceptos')
    q = par(q, 'El filtrado usó dos criterios: los aportes positivos y negativos de cada elemento (se descartaron los de '
               'más factores negativos, como masa excesiva, latencia alta o consumo desproporcionado) y su disposición '
               'para operar en exteriores (se descartaron los vulnerables al viento o a la luz solar directa).')
    q = tabla_movida(q, 'B3', 'Tabla B3', 'Revisión tecnológica y filtrado de conceptos')
    q = sub(q, 'B.4 Significado de cada nivel de la escala de calificación')
    anclas = [
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
    q = tab(q, 'Tabla B4', 'Significado de cada nivel de la escala de 1 a 10', anclas, [1.3, 4.9, 4.9, 4.9])
    q = sub(q, 'B.5 Sensibilidad a la escala')
    pesos8, pesos9 = [10, 9, 9, 8, 9], [10, 10, 8, 8, 9]
    T8 = {'Cámara CSI': [9, 0, 9, 9, 8], 'Cámara web USB': [7, 0, 5, 7, 6], 'Cámara de acción': [4, 0, 2, 3, 5],
          'LiDAR ToF': [0, 9, 9, 9, 8], 'Ultrasónico': [0, 2, 4, 8, 1], 'Radar mmWave': [0, 8, 7, 4, 9]}
    T9 = {'Raspberry Pi 4': [8, 8, 8, 8, 10], 'Jetson Nano': [10, 9, 6, 4, 9], 'Teensy 4.1': [1, 2, 8, 9, 3],
          'YOLO nano': [9, 9, 0, 9, 9], 'EfficientDet/MobileNet': [7, 6, 0, 7, 7], 'UBEC dedicado': [0, 0, 10, 9, 0],
          'Batería secundaria': [0, 0, 7, 3, 0]}
    grupos = [('Cámara', T8, pesos8, ['Cámara CSI', 'Cámara web USB', 'Cámara de acción']),
              ('Distancia', T8, pesos8, ['LiDAR ToF', 'Radar mmWave', 'Ultrasónico']),
              ('Procesador', T9, pesos9, ['Raspberry Pi 4', 'Jetson Nano', 'Teensy 4.1']),
              ('Modelo', T9, pesos9, ['YOLO nano', 'EfficientDet/MobileNet']),
              ('Potencia', T9, pesos9, ['UBEC dedicado', 'Batería secundaria'])]

    def tot(v, w, e5=False):
        return sum((math.ceil(x / 2) if e5 else x) * wi for x, wi in zip(v, w))

    filas = [['Subfunción', 'Alternativa', 'Total 1–10', 'Puesto', 'Total 1–5', 'Puesto']]
    for g, TT, w, alts in grupos:
        s10 = sorted(alts, key=lambda a: -tot(TT[a], w))
        s5 = sorted(alts, key=lambda a: -tot(TT[a], w, True))
        for a in alts:
            filas.append([g, a, tot(TT[a], w), s10.index(a) + 1, tot(TT[a], w, True), s5.index(a) + 1])
    q = par(q, 'Para comprobar que la escala no decide el resultado, las calificaciones de las Tablas de las funciones 1 '
               'y 2 se pasaron a una escala de 1 a 5 (la mitad de la calificación, redondeada hacia arriba) y se '
               'recalcularon los totales con los mismos pesos. Dentro de cada subfunción el orden no cambia.')
    q = tab(q, 'Tabla B5', 'Sensibilidad de la matriz de decisión a la escala de calificación', filas,
            [2.6, 4.4, 2.2, 1.6, 2.2, 1.6])
    q = sub(q, 'B.6 Revisión de la selección con datos medidos')
    filas_r = [['Alternativa', 'Inferencia', 'Latencia', 'Estabilidad de potencia', 'Masa y consumo', 'Python',
                'Total'],
               ['Raspberry Pi 4 (calificación del diseño)', 8, 8, 8, 8, 10, tot([8, 8, 8, 8, 10], pesos9)],
               ['Raspberry Pi 4 (con lo observado en 2.2.5)', 4, 4, 3, 8, 10, tot([4, 4, 3, 8, 10], pesos9)],
               ['Jetson Nano (calificación del diseño)', 10, 9, 6, 4, 9, tot([10, 9, 6, 4, 9], pesos9)],
               ['Jetson Orin Nano (con lo medido)', 10, 10, 8, 5, 9, tot([10, 10, 8, 5, 9], pesos9)]]
    q = tab(q, 'Tabla B6', 'Revisión de la calificación del procesamiento con datos de la integración', filas_r,
            [5.0, 1.8, 1.6, 2.2, 1.8, 1.4, 1.4],
            'Nota. Pesos de la Tabla 7: 10, 10, 8, 8 y 9. [FALTA: confirmar las calificaciones "con lo observado"]')
    q = sub(q, 'B.7 Concepto global del diseño')
    q = figura_movida(q, 'figB1', 'Figura B1', 'Diagrama del concepto global obtenido en el diseño conceptual',
                      'Nota. Corresponde al concepto del diseño, con Raspberry Pi, cámara CSI y TF-Luna. El concepto '
                      'implementado está en la {T:implementado}.')
    q = sub(q, 'B.8 Importancia relativa de los requerimientos operativos')
    q = tabla_movida(q, 'B7', 'Tabla B7', 'Importancia relativa de los requerimientos operativos (QFD)')

    # ================= Anexo C
    q = titulo_anexo(q, 'C', 'Inventario de componentes')
    inv = [['Componente', 'Referencia', 'Cantidad', 'Función'],
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
    q = tab(q, 'Tabla C1', 'Componentes del cuadricóptero integrado', inv, [3.4, 5.6, 1.6, 5.4],
            'Nota. [FALTA: masa de cada subsistema y masa total de despegue]')

    # ================= Anexo D
    q = titulo_anexo(q, 'D', 'Parámetros de ArduPilot y del software')
    pa = [['Parámetro', 'Valor', 'Motivo'],
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
    q = tab(q, 'Tabla D1', 'Parámetros de ArduPilot cambiados o relevantes', pa, [4.8, 4.2, 7.0])
    ps = [['Parámetro del software', 'Valor', 'Dónde se justifica'],
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
    q = tab(q, 'Tabla D2', 'Parámetros del software de a bordo', ps, [6.0, 5.6, 4.4])

    # ================= Anexo E
    q = titulo_anexo(q, 'E', 'Software de percepción, decisión y control')
    q = par(q, 'El código completo está en el repositorio público del proyecto: https://github.com/brahianorrego/Tesis-IA-'
               'Drone (carpetas jetson y simulacion/minimo_tesis). Este anexo presenta su organización, el diagrama de '
               'flujo de la primera versión del detector y los listados de los módulos principales.')
    q = sub(q, 'E.1 Organización del código')
    mods = [['Archivo', 'Qué hace'],
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
    q = tab(q, 'Tabla E1', 'Módulos del software', mods, [6.4, 9.6])
    q = sub(q, 'E.2 Primera versión del detector')
    q = figura_movida(q, 'figE1', 'Figura E1', 'Diagrama de flujo de la primera versión del algoritmo de detección')
    q = sub(q, 'E.3 Listados de código')
    for i, (ruta, titulo) in enumerate([
            ('jetson/lidar_tf.py', 'Lectura del LiDAR TF03'),
            ('jetson/intervencion_banco.py', 'Intervención por MAVLink en banco'),
            ('simulacion/minimo_tesis/decisor_ia.py', 'Clasificador de riesgo'),
            ('simulacion/minimo_tesis/sistema.py', 'Lógica mínima y envolvente de seguridad')], start=1):
        c = M.rotulo_anexo(q, f'Listado E{i}', f'{titulo} ({ruta})')
        lineas = [_limpiar_comentario(x) for x in open(f'{REPO}/{ruta}', encoding='utf-8').read().splitlines()]
        q = M.codigo(c, lineas)

    # ================= Anexo F
    q = titulo_anexo(q, 'F', 'Simulación del protocolo y del clasificador')
    q = sub(q, 'F.1 Modelo de simulación')
    q = par(q, 'La simulación reproduce un dron, una persona o un panel y la lógica de a bordo. La cámara y YOLO se '
               'modelan con una probabilidad de detección que cae con la distancia, ruido en el rumbo y una distancia '
               'estimada por la altura de la caja suponiendo 1.72 m de estatura (campo de visión de 38.9° × 29.7°). El '
               'LiDAR es un solo rayo de 0.1 a 30 m con 2 cm de ruido, inclinado −5°. Las medidas llegan con 100 ms de '
               'retardo. El control reproduce los controladores de posición y actitud de ArduPilot (PSC y ATC) y el '
               'estabilizador BaseCam. Cada variante del protocolo se corre 100 veces con semillas fijas.')
    q = sub(q, 'F.2 Entrenamiento del clasificador')
    q = par(q, 'Los datos salen de vuelos sin intervención en mundos aleatorios: velocidades de 0 a 8 m/s; personas '
               'quietas, que vienen, que cruzan, paralelas o al azar; con o sin panel; y sensores degradados al azar. '
               'Cada cuadro se etiqueta con la verdad del simulador según una pregunta: si el piloto sigue igual, ¿en '
               'los próximos 3 s choca o una persona queda a menos de 2 m? Entrenamiento, validación y prueba usan '
               'mundos distintos.')
    q = tab(q, 'Tabla F1', 'Datos y desempeño del clasificador por cuadro',
            [['Concepto', 'Valor'], ['Arquitectura', 'MLP 32-16, ReLU, 15 entradas, 1 salida'],
             ['Cuadros de entrenamiento', '2 551 725 (13 % con riesgo)'], ['Cuadros de validación', '499 021'],
             ['Cuadros de prueba', '533 085 (12 % con riesgo)'], ['Umbral y persistencia', '0.7 y 2 cuadros'],
             ['Área bajo la curva ROC', '0.974'], ['Precisión media', '0.914'],
             ['Exhaustividad por cuadro', '74.4 %'], ['Precisión', '97.0 %'], ['Falsos positivos', '0.3 %']],
            [7.0, 9.0], 'Nota. La exhaustividad por cuadro no mide la seguridad: un riesgo dura muchos cuadros y basta '
                        'detectarlo en dos seguidos; la seguridad se mide en lazo cerrado.')
    q = tab(q, 'Tabla F2', 'Matriz de confusión en la prueba (por cuadro)',
            [['', 'Predice CONTINUAR', 'Predice DETENER'], ['Sin riesgo real', '470 330', '1 420'],
             ['Con riesgo real', '15 716', '45 619']], [5.0, 5.0, 5.0])
    c = M.rotulo_anexo(q, 'Figura F1', 'Curvas ROC y de precisión-exhaustividad del clasificador')
    fig = M.figura(c, f'{REPO}/simulacion/informes/minimo_tesis_decisor_curvas.png', ancho_cm=15.0, color=AMARILLO)
    q = M.parrafo(fig, '', AMARILLO, estilo='Normal')
    q = sub(q, 'F.3 Protocolo del comité por escenario')
    prot = [['Escenario', '¿Activar?', 'Éxito con el sistema', 'Éxito sin ayuda del operador', 'Vuelo seguro sin el '
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
    q = tab(q, 'Tabla F3', 'Resultados del protocolo del comité en simulación (100 vuelos por variante)', prot,
            [4.6, 1.5, 2.8, 2.6, 2.4, 2.1], 'Nota. Entre corchetes, intervalo de Wilson del 95 %. "Sin ayuda del '
                                            'operador": el operador no apretó la parada en ningún momento.')
    q = sub(q, 'F.4 Mundos de prueba')
    mund = [['Decisor', 'Riesgos no evitados', 'Choques', 'Persona a < 2 m bajo 3.30 m', 'Activaciones innecesarias',
             'Detenido sin necesidad (s)'],
            ['Sin sistema', '2043', '1681', '1488', '—', '—'],
            ['Reglas', '92 (4.5 %)', '39', '420', '137', '2358'],
            ['IA sola', '62 (3.0 %)', '27', '143', '54', '813'],
            ['IA con reglas', '67 (3.3 %)', '28', '218', '67', '1082']]
    q = tab(q, 'Tabla F4', 'Resultados en 3840 vuelos sobre 60 mundos aleatorios de prueba', mund,
            [3.2, 2.6, 1.8, 3.0, 2.8, 2.6], 'Nota. 2043 de los 3840 vuelos (53 %) habrían tenido riesgo físico sin el '
                                            'sistema. Incluye casos físicamente imposibles de evitar.')
    q = sub(q, 'F.5 Condiciones degradadas')
    deg = [['Condición', 'Reglas: éxito · choques · innecesarias', 'IA con reglas: éxito · choques · innecesarias'],
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
    q = tab(q, 'Tabla F5', 'Desempeño con sensores degradados (18 variantes de 100 vuelos por condición)', deg,
            [6.0, 5.0, 5.0], 'Nota. Combinada: recall 0.85, medio cuerpo, LiDAR degradado, 200 ms y viento de 4 m/s.')
    q = sub(q, 'F.6 Velocidad máxima segura')
    vel = [['Condición', 'Panel fijo', 'Persona quieta', 'Persona que corre hacia el dron'],
           ['C0 Nominal', '11', '4', '10'], ['C6 Latencia de 200 ms', '11', '4', '9'],
           ['C7 Latencia de 300 ms', '10', '4', '7'], ['C10 Combinada', '11', '4', '8'],
           ['C11 Recall 0.40', '11', '4', '7'], ['C12 Solo cabeza y hombros', '11', '4', '0'],
           ['C13 Latencia de 500 ms', '10', '4', '5']]
    q = tab(q, 'Tabla F6', 'Velocidad máxima de avance (m/s) a la que las reglas detienen el dron con margen', vel,
            [6.0, 3.0, 3.0, 4.0], 'Nota. Barrido de 1 a 12 m/s; segura si esa velocidad y todas las menores cumplen en '
                                  'al menos el 95 % de los vuelos. Con IA y reglas, frente a una persona quieta, sube a '
                                  '12 m/s.')
    q = sub(q, 'F.7 Pruebas estadísticas')
    q = par(q, 'Las proporciones se reportan con el intervalo de Wilson del 95 %. La comparación entre decisores en los '
               'escenarios de discriminación usa la prueba exacta de McNemar sobre los 500 vuelos emparejados (mismas '
               'semillas): en 16 vuelos acertó la IA con reglas y fallaron las reglas, y en 2 ocurrió lo contrario (p = '
               '0.0013). La misma comparación tratada como dos muestras independientes da p = 0.09, porque no aprovecha '
               'el emparejamiento. En los 3840 vuelos no se dispone del archivo por vuelo, así que se usó la prueba de '
               'dos proporciones: choques, p ≈ 0.18; personas a menos de 2 m, p < 0.001; riesgos no evitados, p ≈ 0.045.')

    # ================= Anexo G
    q = titulo_anexo(q, 'G', 'Protocolo de pruebas de campo')
    q = sub(q, 'G.1 Lista de verificación antes de cada jornada')
    for t in ['Zona consultada en el Visor Geográfico UAS, sin restricciones; permiso del dueño del terreno.',
              'Pronóstico revisado; viento medido con anemómetro por debajo del límite fijado [FALTA: límite de viento '
              'en m/s].', 'Zona delimitada y señalizada; ningún tercero dentro de ella.',
              'Batería cargada y medida (tensión por celda); batería de repuesto en bolsa ignífuga.',
              'Hélices, tornillos y amarres revisados; estabilizador y LiDAR firmes.',
              'Geocerca de ArduPilot activa; LOIT_SPEED en 4 m/s; modos del interruptor comprobados.',
              'Parada de emergencia (CH8) probada en tierra antes de cada vuelo.',
              'Registro de la Jetson y DataFlash funcionando; reloj del sistema sincronizado.',
              'Fijación GPS 3D antes de activar el modo experimental.',
              'Piloto de seguridad y observador presentes; consentimientos firmados de los voluntarios.']:
        q = M.vineta(q, t)
    q = sub(q, 'G.2 Planilla de registro por repetición')
    plan = [['Campo', 'Valor'], ['Fecha y hora', ''], ['Escenario y repetición', ''], ['Velocidad de avance (m/s)', ''],
            ['Viento (m/s) e iluminación', ''], ['¿Se activó el sistema?', ''], ['¿Debía activarse?', ''],
            ['Choque o contacto', ''], ['Latencia riesgo → orden (ms, del registro)', ''],
            ['Distancia mínima (m, marcas en el suelo o video)', ''], ['Parada o retoma del operador', ''],
            ['Observaciones (estabilidad, fallas, comportamiento inesperado)', '']]
    q = tab(q, 'Tabla G1', 'Planilla de registro de cada repetición', plan, [8.0, 8.0])
    q = sub(q, 'G.3 Disposición del campo')
    q = par(q, 'Campo abierto y plano, sin público. Un panel de 2 × 2.6 m (cartón pluma o lona sobre un marco) a 20 m del '
               'punto de partida. Conos a 2, 4, 6, 8, 10, 12 y 15 m sobre la trayectoria, medidos con cinta, para estimar '
               'distancias en el video. Primero se usa un maniquí o una silueta de 1.7 m; una persona real solo después '
               'de diez éxitos de diez con el maniquí, y siempre con la parada de emergencia en la mano del operador.')
    q = sub(q, 'G.4 Criterios de interrupción')
    for t in ['Viento por encima del límite o lluvia.', 'Un tercero entra en la zona.',
              'Batería por debajo de 3.5 V por celda o aviso de failsafe.',
              'Comportamiento inesperado del dron o pérdida del enlace MAVLink.',
              'Cualquier contacto con una persona, el maniquí o el panel: se suspende la jornada y se analiza el '
              'registro antes de seguir.']:
        q = M.vineta(q, t)
    q = sub(q, 'G.5 Consentimiento informado para el uso de imagen')
    for t in ['Yo, ____________________, identificado(a) con documento n.° ____________, acepto participar como '
              'voluntario(a) en los ensayos del proyecto de grado "Implementación experimental de un sistema de detección '
              'y evasión mediante un modelo de inteligencia artificial para un cuadricóptero" de la Universidad de San '
              'Buenaventura.',
              'Entiendo que el dron se acercará a mí en un entorno controlado, que el piloto puede detenerlo en '
              'cualquier momento y que puedo retirarme cuando quiera. Autorizo que se grabe mi imagen solo con fines '
              'académicos, conforme a la Ley 1581 de 2012; los videos se guardarán con acceso restringido y no se '
              'publicarán sin mi autorización.',
              'Firma: ____________________    Fecha: ____________']:
        q = par(q, t)
    return q
