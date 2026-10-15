"""Referencias y anexos A a G."""
import copy
import os
import re
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
        M.run(p, f'Anexo {M.ANEXO_NUM[letra]}. {nombre}', AMARILLO, bold=True)
        M.marcador(p, f'Anexo_{letra}')
        return p

    def sub(ancla, texto):
        p = M.parrafo(ancla, '', AMARILLO, estilo='Normal')
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.keep_with_next = True
        M.run(p, re.sub(r'^[A-I]\.\d+ ', '', texto), AMARILLO, bold=True)
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

    FOTOS = os.environ.get('FOTOS', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fotos'))

    def figura_foto(q, etiqueta, titulo, archivo, ancho_cm, nota):
        c = M.rotulo_anexo(q, etiqueta, titulo)
        fig = M.figura(c, os.path.join(FOTOS, archivo), ancho_cm=ancho_cm, color=AMARILLO)
        return M.nota(fig, nota)

    def figura_antecedente(q, k, etiqueta, titulo):
        c = M.rotulo_anexo(q, etiqueta, titulo)
        e = copy.deepcopy(M.extra['img_fig'][k])
        for b_ in list(e.iter(qn('w:bookmarkStart'))) + list(e.iter(qn('w:bookmarkEnd'))):
            b_.getparent().remove(b_)
        for r in e.iter(qn('w:r')):
            Run(r, None).font.highlight_color = AMARILLO
        c._p.addnext(e)
        return M.nota(e, M.extra['notas_fig'][k])

    # ================= Anexo A: antecedentes ampliados
    def anexo_A(q):
        q = titulo_anexo(q, 'A', 'Antecedentes ampliados')
        q = par(q, 'Este anexo amplía los antecedentes del apartado 1.5. Describe cada trabajo con más detalle, reúne las '
                   'figuras de las fuentes y compara qué aporta cada uno frente a lo que se hace aquí.')
        q = sub(q, 'Antecedentes internacionales')
        q = par(q, 'Falanga et al. (2017) estudian el vuelo de un cuadricóptero sin GNSS en una maniobra exigente: pasar '
                   'por una abertura estrecha con sensado y procesamiento a bordo. Muestran que la maniobra es posible '
                   'cuando visión, estimación y control están bien integrados, y que la percepción y la latencia del '
                   'procesamiento influyen directamente en la seguridad. La {F:fA1} muestra la secuencia de la maniobra.')
        q = figura_antecedente(q, 'falanga', 'Figura A1', 'Secuencia del vuelo del cuadricóptero a través de una '
                                                         'abertura estrecha')
        q = par(q, 'Valenti et al. (2018) proponen una arquitectura modular para UAV que integra percepción, localización '
                   'y evitación en entornos congestionados y sin referencia satelital. Su aporte es la organización '
                   'explícita del flujo de información entre módulos, la misma idea con la que se estructura este sistema.')
        q = par(q, 'En una revisión sistemática de 85 publicaciones sobre detección visual de obstáculos para evitar '
                   'colisiones en vuelo, Vera-Yanez et al. (2023) encuentran un crecimiento sostenido del campo, sobre todo '
                   'en detección y seguimiento, y una brecha: la mayoría de las propuestas se valida en simulación y solo '
                   'una fracción menor en vehículos reales. La {F:fA2} sintetiza la clasificación de los trabajos revisados.')
        q = figura_antecedente(q, 'vera', 'Figura A2', 'Clasificación general de trabajos en detección visual de '
                                                       'obstáculos para evitar colisiones en vuelo')
        q = par(q, 'Merei et al. (2025) plantean que la evasión de obstáculos sigue siendo uno de los desafíos centrales '
                   'para operar UAV con seguridad, tanto frente a obstáculos estáticos como dinámicos, y que el diseño debe '
                   'equilibrar la capacidad de detección, la complejidad del algoritmo y la viabilidad en plataformas '
                   'reales. La {F:fA3} recoge su clasificación de métodos.')
        q = figura_antecedente(q, 'merei', 'Figura A3', 'Clasificación general de métodos de detección y evasión de '
                                                        'obstáculos en UAV')
        q = sub(q, 'Antecedentes nacionales')
        q = par(q, 'Gallo Sanabria et al. (2020) proponen un seguimiento de trayectoria para un UAV basado en visión '
                   'artificial. Su objetivo es seguir una ruta y no evitar obstáculos, pero muestra cómo la visión por '
                   'computador genera acciones de control sobre una plataforma aérea ({F:fA4}).')
        q = figura_antecedente(q, 'gallo', 'Figura A4', 'Esquema general del sistema de seguimiento de trayectoria '
                                                        'basado en visión artificial para un UAV')
        q = par(q, 'Bohórquez Caro (2021) desarrolla una solución embebida que da a un cuadricóptero la capacidad de '
                   'detectar y seguir un objetivo móvil con ROS. Se orienta al seguimiento y no a la evasión, pero muestra '
                   'que es viable integrar procesamiento visual, entorno robótico y arquitectura UAV en un contexto '
                   'colombiano.')
        q = par(q, 'Avilés Correa y Garzón Bernal [FALTA: año, tomado del repositorio de la Fundación Universitaria Los '
                   'Libertadores] desarrollan en Bogotá un sistema de detección y evasión de obstáculos que integra cámara, '
                   'LiDAR y sensor infrarrojo para generar señales de control. La plataforma es de ala fija y no un '
                   'cuadricóptero, pero es de los antecedentes más cercanos: trata de forma explícita la detección y la '
                   'evasión con sensado combinado y lógica de decisión.')
        q = sub(q, 'Antecedentes locales y departamentales')
        q = par(q, 'Córdoba Velásquez y Ruiz Rincón (2023) desarrollan en la Universidad de San Buenaventura un dispositivo '
                   'auditivo que apoya la navegación en interiores de personas con discapacidad visual, con visión '
                   'artificial, YOLOv5 y Python. No es una aplicación aérea, pero valida la detección visual de personas en '
                   'tiempo real y muestra una integración funcional entre sensado, procesamiento y respuesta, aunque se '
                   'validó en interiores.')
        q = par(q, 'Castro Gutiérrez y Ortega Hernández (2017) desarrollan en la misma universidad una interfaz '
                   'cerebro-computador para controlar la elevación y el avance de un cuadricóptero. No usan visión por '
                   'computador, pero muestran la experiencia previa de la universidad en la integración de control y '
                   'plataforma de vuelo sobre un cuadricóptero.')
        q = par(q, 'León Mondragón y Rojas Díaz [FALTA: año] usan aeronaves no tripuladas y fotogrametría digital para '
                   'identificar zonas de riesgo en el cerro Casablanca, en Madrid (Cundinamarca). No tratan la evasión de '
                   'obstáculos, pero son un antecedente departamental del uso de UAS en un escenario real, con énfasis en '
                   'el diseño metodológico y en la recolección ordenada de datos.')
        q = sub(q, 'Comparación de los antecedentes')
        q = par(q, 'La {T:tA1} resume qué hace cada trabajo y cómo se relaciona con este. Ninguno reúne, en un '
                   'cuadricóptero, la detección de personas con un modelo preentrenado, un LiDAR de proximidad, una decisión '
                   'aprendida acotada por reglas de seguridad y una validación repetible en exteriores. [REVISAR: confirmar '
                   'cada fila leyendo la fuente completa antes de entregar]')
        filas = [['Ámbito', 'Trabajo', 'Qué hace', 'Relación con este trabajo'],
                 ['Internacional', 'Falanga et al. (2017)', 'Vuelo de un cuadricóptero por aberturas estrechas, con sensado y cómputo a bordo y sin GNSS', 'Muestra que la latencia del procesamiento condiciona la seguridad'],
                 ['Internacional', 'Valenti et al. (2018)', 'Arquitectura modular de percepción, localización y evitación sin GPS', 'Misma organización en módulos con interfaces definidas'],
                 ['Internacional', 'Vera-Yanez et al. (2023)', 'Revisión de 85 trabajos de detección visual de obstáculos', 'La mayoría se valida en simulación: justifica probar en una aeronave real'],
                 ['Internacional', 'Merei et al. (2025)', 'Revisión de métodos de detección y evasión en UAV', 'La evasión sigue abierta; pide equilibrar detección, complejidad y viabilidad a bordo'],
                 ['Nacional', 'Gallo Sanabria et al. (2020)', 'Seguimiento de trayectoria de un UAV con visión artificial', 'Cámara que genera acciones de control; sigue una ruta, no evita obstáculos'],
                 ['Nacional', 'Bohórquez Caro (2021)', 'Detección y seguimiento de un objetivo móvil desde un UAV con visión embebida y ROS', 'Integra visión embebida y arquitectura de vuelo; no trata la evasión'],
                 ['Nacional', 'Avilés Correa y Garzón Bernal', 'Detección y evasión de obstáculos de bajo costo con cámara, LiDAR e infrarrojo', 'El más cercano; plataforma de ala fija'],
                 ['Local', 'Córdoba Velásquez y Ruiz Rincón (2023)', 'Detección de personas con YOLOv5 en un dispositivo auditivo para interiores', 'Detecta personas en tiempo real; no es una aeronave'],
                 ['Local', 'Castro Gutiérrez y Ortega Hernández (2017)', 'Control de elevación y avance de un cuadricóptero con una interfaz cerebro-computador', 'Experiencia institucional con el cuadricóptero; sin visión por computador'],
                 ['Departamental', 'León Mondragón y Rojas Díaz', 'UAS y fotogrametría para identificar zonas de riesgo en Madrid (Cundinamarca)', 'Uso de UAS en un escenario real; no trata la evasión']]
        q = tab(q, 'Tabla A1', 'Qué hace cada antecedente y cómo se relaciona con este trabajo', filas, [2.3, 3.6, 5.4, 4.7])
        q = sub(q, 'Búsqueda de antecedentes')
        q = par(q, '[FALTA: describir la búsqueda hecha para el estado del arte: bases de datos consultadas, palabras clave, '
                   'años y criterios de selección. Con eso se respalda que el tema está poco estudiado.]')
        return q

    # ================= Anexo H: marcos teórico y conceptual ampliados
    def anexo_H(q):
        q = titulo_anexo(q, 'H', 'Marcos teórico y conceptual ampliados')
        q = par(q, 'Este anexo desarrolla los apartados 1.6 y 1.7. Las ecuaciones están en el cuerpo del documento y aquí se '
                   'explican con más detalle.')
        q = sub(q, 'Marco teórico')
        q = sub(q, 'Detección de personas con YOLO y COCO')
        q = par(q, 'YOLO formula la detección como una regresión directa desde la imagen completa hacia cajas delimitadoras '
                   'y probabilidades de clase, de modo que una sola red predice la localización y la clasificación en una '
                   'única evaluación. Esa característica reúne velocidad y detección en tiempo real, y por eso YOLO es una '
                   'referencia para aplicaciones con restricciones de tiempo (Redmon et al., 2016).')
        q = par(q, 'COCO es un conjunto de datos de referencia en visión por computador que incluye la clase *person* '
                   '(Lin et al., 2014). Usar un modelo preentrenado en COCO permite detectar personas sin construir una base '
                   'de datos propia y concentra el esfuerzo del trabajo en la integración y la validación.')
        q = sub(q, 'Variables geométricas y región de observación')
        q = par(q, 'A partir de la caja se obtienen el centroide y el área. El centroide ubica a la persona en la imagen y el '
                   'área sirve como medida cualitativa de cercanía aparente. Usar características de la imagen como '
                   'variables de realimentación es la base del control servo visual (Chaumette & Hutchinson, 2006), pero '
                   'aquí solo dan una base geométrica mínima, no un seguimiento avanzado. Cuando se define una región de '
                   'observación, la detección es válida solo si el centroide cae dentro de ella, lo que enlaza la salida '
                   'del detector con la zona del escenario de prueba.')
        q = sub(q, 'Distancia frontal con LiDAR de tiempo de vuelo')
        q = par(q, 'El LiDAR de tiempo de vuelo emite un pulso de luz y estima la distancia con el tiempo que tarda en ir al '
                   'objeto y volver (Brand, 2021). En este sistema no sirve para reconstruir el entorno: entrega una '
                   'variable simple y confiable que activa una respuesta de seguridad con un umbral de distancia. Eso '
                   'coincide con el alcance, que no incluye planeación tridimensional ni mapeo.')
        q = sub(q, 'Lógica de decisión y prioridad de seguridad')
        q = par(q, 'El sistema se modela con eventos discretos: ciertas entradas producen transiciones entre estados de '
                   'operación. Con la presencia válida de una persona y la condición de riesgo frontal como entradas, la '
                   'salida es el comando del piloto o la respuesta automática, según haya o no riesgo. En el modo '
                   'experimental la lógica de seguridad tiene prioridad en el tiempo sobre el comando de avance. Como el '
                   'protocolo limita la prueba al avance frontal y a la evasión vertical, esa respuesta es una secuencia de '
                   'detención y ascenso. La expresión formaliza el criterio de decisión y no modela un controlador de vuelo.')
        q = sub(q, 'Latencia del ciclo percepción–decisión–control')
        q = par(q, 'El tiempo total del ciclo es la suma de captura, inferencia, decisión, comunicación y ejecución. '
                   'Separar las etapas permite ver cuál limita la respuesta y justifica un modelo ligero, reglas simples de '
                   'decisión y una integración directa con la controladora: si una etapa se alarga, el sistema reacciona '
                   'más tarde ante una obstrucción.')
        q = sub(q, 'Marco conceptual')
        q = sub(q, 'Vehículo aéreo no tripulado y operación en exteriores')
        q = par(q, 'Un vehículo aéreo no tripulado es una aeronave que opera sin piloto a bordo y cuya trayectoria guía un '
                   'operador o un sistema automático. Aquí interesa un cuadricóptero experimental, operado al aire libre en '
                   'un entorno exterior controlado donde las condiciones de ensayo se definen de antemano y se pueden '
                   'repetir.')
        q = par(q, 'La operación en exteriores es la ejecución de pruebas al aire libre en una zona delimitada, señalizada e '
                   'inspeccionada antes de volar, con obstáculos tipo panel, trayectoria de avance frontal, márgenes de '
                   'seguridad fijados antes de cada ensayo y registro del viento y la iluminación de la jornada. El objetivo '
                   'es evaluar si el sistema responde con seguridad ante personas y obstrucciones en una misión '
                   'específica, sin resolver navegación global ni posicionamiento autónomo.')
        q = sub(q, 'Controladora de vuelo y comunicación MAVLink')
        q = par(q, 'La controladora tipo Pixhawk es responsable del control de bajo nivel: estabilización, sensado interno, '
                   'armado, modos de vuelo y respuesta básica. No hace la detección visual ni la decisión principal; recibe '
                   'y ejecuta las órdenes del módulo de decisión. El enlace MAVLink con la computadora de a bordo '
                   'transporta información de estado y comandos, de modo que las decisiones de percepción y decisión se '
                   'reflejan en el comportamiento del cuadricóptero.')
        q = sub(q, 'Percepción visual, YOLO preentrenado y evasión básica')
        q = par(q, 'La percepción visual transforma las imágenes de la cámara en información para decidir. Aquí se limita a '
                   'detectar personas y estimar su posición aproximada en la imagen; no incluye reconocimiento completo del '
                   'entorno ni navegación visual. Hablar de un YOLO preentrenado en COCO significa trabajar con un modelo ya '
                   'entrenado por terceros, usado solo para inferencia, y eso delimita el trabajo: no es una investigación '
                   'sobre entrenamiento de modelos.')
        q = par(q, 'La evasión básica es una respuesta automática de seguridad ante una condición de riesgo en la '
                   'trayectoria de avance. Se restringe a detener el avance y ascender verticalmente dentro de un margen '
                   'seguro, y eso la diferencia de las propuestas de evasión en varias direcciones o de navegación '
                   'autónoma integral.')
        return q

    # ================= Anexo I: marco normativo ampliado
    def anexo_I(q):
        q = titulo_anexo(q, 'I', 'Marco normativo ampliado')
        q = par(q, 'Este anexo desarrolla el apartado 1.8.')
        q = sub(q, 'Referente internacional')
        q = par(q, 'El artículo 8 del Convenio sobre Aviación Civil Internacional dispone que ninguna aeronave capaz de volar '
                   'sin piloto puede operar sobre el territorio de un Estado contratante sin su autorización especial y '
                   'conforme a las condiciones de esa autorización. Agrega que, en regiones abiertas a la aviación civil, el '
                   'vuelo debe controlarse para que no sea un peligro para otras aeronaves (Organización de Aviación Civil '
                   'Internacional [OACI], [FALTA: año de la edición consultada]). Este trabajo lo toma como base para que '
                   'toda operación experimental al aire libre se haga con control, seguridad y responsables definidos.')
        q = sub(q, 'RAC 100 y verificación del espacio aéreo')
        q = par(q, 'En Colombia, la norma para aeronaves no tripuladas es el RAC 100, Operación de Sistemas de Aeronaves no '
                   'Tripuladas UAS (Unidad Administrativa Especial de Aeronáutica Civil, 2023). La página de normatividad de '
                   'la Aerocivil lo presenta como el reglamento vigente y reporta su actualización más reciente el 24 de '
                   'abril de 2024 [REVISAR: confirmar la fecha y la versión consultadas]. Se adopta como referencia aunque '
                   'el trabajo sea un ensayo académico y no una operación comercial.')
        q = par(q, 'Antes de cada jornada se verifican la clasificación del espacio aéreo, la distancia mínima a personas y '
                   'edificaciones ajenas a la prueba, el límite de altura y la ausencia de restricciones geográficas, con el '
                   'Visor Geográfico UAS como herramienta de consulta. Los vuelos se mantienen dentro de la línea de vista '
                   'del piloto (VLOS), sin operaciones más allá de ella (BVLOS) y sin sobrevolar grupos de personas.')
        q = sub(q, 'Alcance práctico para una prueba académica')
        q = par(q, 'Como no hay transporte de carga, uso comercial ni navegación autónoma completa, el RAC 100 se toma como '
                   'guía de buenas prácticas: control del vehículo, línea de vista, zona delimitada y señalizada, consulta '
                   'previa de restricciones, supervisión permanente del operador y una misión clara y verificable.')
        q = par(q, 'La Aerocivil publica además las circulares informativas 100-MAUT-5.0-22-010-CI, sobre el registro de '
                   'sistemas UAS y equipos tecnológicos, y 100-MAUT-5.0-22-009-CI, sobre el certificado de idoneidad del '
                   'piloto UAS. Aplican porque los ensayos son al aire libre: orientan el registro de la aeronave y la '
                   'acreditación del piloto que ejecuta las pruebas. [FALTA: número de registro del cuadricóptero y '
                   'certificado de idoneidad del piloto, o la indicación de que están en trámite]')
        q = sub(q, 'Seguridad y salud en el trabajo')
        q = par(q, 'El Decreto 1072 de 2015 define la seguridad y salud en el trabajo como la disciplina que previene '
                   'lesiones y enfermedades causadas por las condiciones de trabajo, y la organiza como un proceso por '
                   'etapas, basado en la mejora continua, que anticipa, reconoce, evalúa y controla los riesgos '
                   '(Ministerio del Trabajo, 2015). Exige identificar peligros, valorar riesgos y definir controles, y fijar '
                   'planes, objetivos, responsables e indicadores.')
        q = par(q, 'Aplicado a los ensayos, esto significa delimitar y señalizar la zona, inspeccionar la aeronave antes de '
                   'volar, controlar el acceso de terceros, revisar el clima, definir altura y trayectoria, contar con un '
                   'piloto de seguridad, fijar criterios para interrumpir el ensayo y registrar los incidentes. La '
                   'validación involucra equipo rotatorio, energía, movimiento aéreo y personas en el entorno, y por eso el '
                   'marco normativo no se limita a la regulación aeronáutica.')
        q = sub(q, 'Protección de datos personales e imagen')
        q = par(q, 'La Ley Estatutaria 1581 de 2012 establece el régimen general de protección de datos personales en '
                   'Colombia: desarrolla el derecho a conocer, actualizar y rectificar la información recogida sobre las '
                   'personas y regula el tratamiento de los datos, sus principios y los deberes del responsable (Congreso de '
                   'la República de Colombia, 2012). Como el sistema detecta personas en video y los ensayos se graban, '
                   'cualquier captura en la que alguien sea identificable se maneja con finalidad académica, consentimiento '
                   'previo, acceso restringido y sin divulgación no autorizada. El formato de consentimiento está en el '
                   'Anexo G.')
        return q

    def anexo_B(q):
        q = titulo_anexo(q, 'B', 'Diseño conceptual: sensibilidad y revisión de la selección')
        q = par(q, 'Este anexo complementa el apartado 2.1 con dos comprobaciones: la prueba de que la escala de '
                   'calificación no decide el resultado y la revisión de la selección con datos medidos en la '
                   'integración.')
        q = sub(q, 'Sensibilidad a la escala')
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
                   'recalcularon los totales con los mismos pesos. Dentro de cada subfunción el orden no cambia. La {T:tB5} '
                   'da los totales en las dos escalas.')
        q = tab(q, 'Tabla B5', 'Sensibilidad de la matriz de decisión a la escala de calificación', filas,
                [2.6, 4.4, 2.2, 1.6, 2.2, 1.6])
        q = sub(q, 'Revisión de la selección con datos medidos')
        q = par(q, 'La {T:tB6} repite la calificación del procesamiento con lo observado en la integración: la Raspberry Pi 4 '
                   'tuvo caídas de tensión, fallos de arranque y un cuello de botella en la inferencia, y la Jetson Orin '
                   'Nano procesó cada cuadro en 9 a 11 ms.')
        filas_r = [['Alternativa', 'Inferencia', 'Latencia', 'Estabilidad de potencia', 'Masa y consumo', 'Python',
                    'Total'],
                   ['Raspberry Pi 4 (calificación del diseño)', 8, 8, 8, 8, 10, tot([8, 8, 8, 8, 10], pesos9)],
                   ['Raspberry Pi 4 (con lo observado en 2.2.5)', 4, 4, 3, 8, 10, tot([4, 4, 3, 8, 10], pesos9)],
                   ['Jetson Nano (calificación del diseño)', 10, 9, 6, 4, 9, tot([10, 9, 6, 4, 9], pesos9)],
                   ['Jetson Orin Nano (con lo medido)', 10, 10, 8, 5, 9, tot([10, 10, 8, 5, 9], pesos9)]]
        q = tab(q, 'Tabla B6', 'Revisión de la calificación del procesamiento con datos de la integración', filas_r,
                [5.0, 1.8, 1.6, 2.2, 1.8, 1.4, 1.4],
                'Nota. Pesos de la {T:pesos}: 10, 10, 8, 8 y 9. [FALTA: confirmar las calificaciones "con lo observado"]')
        return q

    def anexo_C(q):
        q = titulo_anexo(q, 'C', 'Fotografías del ensamble del cuadricóptero')
        q = par(q, 'Este anexo reúne las fotografías del armado. El inventario de componentes, la masa medida y el módulo '
                   'GPS están en el apartado 2.2.1, y el procedimiento de armado se describe allí mismo.')
        q = sub(q, 'Fotografías del ensamble')
        q = par(q, '[FALTA: fotografías del montaje por etapas (estado inicial desarmado, motores y variadores, placa de '
                   'distribución, Power Module, Pixhawk, estabilizador, Jetson y aeronave terminada), cada una con su '
                   'figura, una frase que la explique antes y la nota de fuente]')
        return q

    def anexo_D(q):
        q = titulo_anexo(q, 'D', 'Parámetros del software de a bordo')
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
        q = par(q, 'Los valores del software de a bordo, con el apartado donde se justifica cada uno, están en la {T:tD2}.')
        q = tab(q, 'Tabla D2', 'Parámetros del software de a bordo', ps, [6.0, 5.6, 4.4])
        return q

    def anexo_E(q):
        q = titulo_anexo(q, 'E', 'Software de percepción, decisión y control')
        q = par(q, 'El código completo está en el repositorio público del proyecto: https://github.com/brahianorrego/Tesis-IA-'
                   'Drone (carpetas jetson y simulacion/minimo_tesis). Este anexo presenta los listados de los módulos principales.')
        q = par(q, 'La organización de los módulos está en la {T:modulos}, en el apartado 2.2.6.')
        q = sub(q, 'E.2 Primera versión del detector')
        q = par(q, 'El diagrama de flujo de la primera versión del detector está en el apartado 2.2.4.')
        q = sub(q, 'E.3 Listados de código')
        for i, (ruta, titulo) in enumerate([
                ('jetson/lidar_tf.py', 'Lectura del LiDAR TF03'),
                ('jetson/intervencion_banco.py', 'Intervención por MAVLink en banco'),
                ('simulacion/minimo_tesis/decisor_ia.py', 'Clasificador de riesgo'),
                ('simulacion/minimo_tesis/sistema.py', 'Lógica mínima y envolvente de seguridad')], start=1):
            c = M.rotulo_anexo(q, f'Listado E{i}', f'{titulo} ({ruta})')
            lineas = [_limpiar_comentario(x) for x in open(f'{REPO}/{ruta}', encoding='utf-8').read().splitlines()]
            q = M.codigo(c, lineas)
        return q

    def anexo_F(q):
        q = titulo_anexo(q, 'F', 'Simulación del protocolo y del clasificador')
        q = par(q, 'Este anexo describe el simulador y la estadística. Los resultados están en el capítulo 3 y los datos del '
                   'clasificador, en el apartado 2.2.6.')
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
        q = sub(q, 'F.7 Pruebas estadísticas')
        q = par(q, 'Las proporciones se reportan con el intervalo de Wilson del 95 %. La comparación entre decisores en los '
                   'escenarios de discriminación usa la prueba exacta de McNemar sobre los 500 vuelos emparejados (mismas '
                   'semillas): en 16 vuelos acertó la IA con reglas y fallaron las reglas, y en 2 ocurrió lo contrario (p = '
                   '0.0013). La misma comparación tratada como dos muestras independientes da p = 0.09, porque no aprovecha '
                   'el emparejamiento. En los 3840 vuelos no se dispone del archivo por vuelo, así que se usó la prueba de '
                   'dos proporciones: choques, p ≈ 0.18; personas a menos de 2 m, p < 0.001; riesgos no evitados, p ≈ 0.045.')
        return q

    def anexo_G(q):
        q = titulo_anexo(q, 'G', 'Formatos de las pruebas de campo')
        q = par(q, 'Este anexo reúne los dos formatos que se usan en cada jornada: la planilla de registro y el consentimiento '
                   'informado. La lista de verificación, la disposición del campo y los criterios de interrupción están en '
                   'el apartado 2.3.5.')
        q = sub(q, 'G.2 Planilla de registro por repetición')
        plan = [['Campo', 'Valor'], ['Fecha y hora', ''], ['Escenario y repetición', ''], ['Velocidad de avance (m/s)', ''],
                ['Viento (m/s) e iluminación', ''], ['¿Se activó el sistema?', ''], ['¿Debía activarse?', ''],
                ['Choque o contacto', ''], ['Latencia riesgo → orden (ms, del registro)', ''],
                ['Distancia mínima (m, marcas en el suelo o video)', ''], ['Parada o retoma del operador', ''],
                ['Observaciones (estabilidad, fallas, comportamiento inesperado)', '']]
        q = par(q, 'La {T:tG1} es la planilla que se llena en cada repetición.')
        q = tab(q, 'Tabla G1', 'Planilla de registro de cada repetición', plan, [8.0, 8.0])
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

    q = P[590]
    q = M.parrafo(q, '', AMARILLO, estilo='Normal')  # ancla para los anexos
    for f in (anexo_H, anexo_I, anexo_G, anexo_B, anexo_C, anexo_D, anexo_E, anexo_F):
        q = f(q)
    return q
