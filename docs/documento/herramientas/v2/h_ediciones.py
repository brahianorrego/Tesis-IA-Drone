"""Ediciones de redacción (skill humanizer). Cada una: (fragmento viejo, fragmento nuevo)."""
E = [
    # --- Introducción ---
    ("Detectar no basta. Muchos desarrollos muestran que un modelo reconoce personas en un video, pero no llegan a convertir esa información en una orden que la aeronave ejecute con un retardo aceptable.",
     "En muchos desarrollos el modelo reconoce personas en un video, pero esa información no llega a convertirse en una orden que la aeronave ejecute con un retardo aceptable."),
    # --- 1. Planteamiento ---
    ("La dificultad no está en detectar a una persona dentro de una imagen, algo que los modelos actuales hacen bien (Redmon et al., 2016; Lin et al., 2014), sino en convertir esa detección en una acción segura.",
     "Los modelos actuales detectan bien a una persona dentro de una imagen (Redmon et al., 2016; Lin et al., 2014); lo difícil es convertir esa detección en una acción segura."),
    ("La respuesta se limita a detener el avance y ascender; no se busca una navegación autónoma completa.",
     "La respuesta se limita a detener el avance y ascender."),
    # --- 1.1 Justificación ---
    ("La propuesta, además, es alcanzable y medible. No pretende resolver la navegación autónoma, sino demostrar en exteriores, con un protocolo repetible, que la arquitectura reacciona ante personas y obstrucciones en una trayectoria de avance frontal. Sus resultados pueden servir de base a trabajos posteriores sobre percepción y control de cuadricópteros.",
     "El alcance es modesto y medible: demostrar en exteriores, con un protocolo repetible, que la arquitectura reacciona ante personas y obstrucciones en una trayectoria de avance frontal. Los resultados pueden servir de punto de partida para trabajos posteriores sobre percepción y control de cuadricópteros."),
    # --- 1.5 Estado del arte ---
    ("Su revisión ayuda a ubicar este trabajo: las decisiones de diseño deben equilibrar la capacidad de detección, la complejidad del algoritmo y la posibilidad real de implementarlo a bordo.",
     "De ahí que las decisiones de diseño de este trabajo busquen un equilibrio entre la capacidad de detección, la complejidad del algoritmo y la posibilidad real de implementarlo a bordo."),
    ("pero también una distancia entre la demostración del algoritmo", "y también una distancia entre la demostración del algoritmo"),
    ("no busca una navegación autónoma completa, sino integrar detección de personas, sensado de proximidad y una maniobra básica de evasión en un cuadricóptero, y probarla en exteriores con un protocolo repetible.",
     "integra detección de personas, sensado de proximidad y una maniobra básica de evasión en un cuadricóptero, y la prueba en exteriores con un protocolo repetible."),
    # --- 1.6 Marco teórico ---
    ("El objetivo no es entrenar un detector, sino integrar uno disponible en una plataforma real; la versión usada",
     "Aquí no se entrena un detector: se integra uno disponible en una plataforma real. La versión usada"),
    ("El sistema no se basa en una ley de navegación autónoma, sino en una lógica discreta que vigila la detección y la proximidad. Se puede ver",
     "La lógica del sistema es discreta: vigila la detección y la proximidad y no incluye ninguna ley de navegación autónoma. Se puede ver"),
    # --- 1.7 Marco conceptual ---
    ("No se trata de navegación global ni de posicionamiento autónomo, sino de comprobar si el sistema responde con seguridad ante personas y obstrucciones en una misión específica.",
     "El ensayo no incluye navegación global ni posicionamiento autónomo; solo comprueba si el sistema responde con seguridad ante personas y obstrucciones en una misión específica."),
    ("no detecta personas ni decide la maniobra, sino que recibe las órdenes del módulo de decisión y mantiene la aeronave estable mientras las ejecuta.",
     "no detecta personas ni decide la maniobra: recibe las órdenes del módulo de decisión y mantiene la aeronave estable mientras las ejecuta."),
    ("No es navegación autónoma ni planeación libre de trayectorias: es una acción predefinida que se activa cuando el sistema identifica una proximidad peligrosa.",
     "Es una acción predefinida, y no navegación autónoma ni planeación libre de trayectorias, que se activa cuando el sistema identifica una proximidad peligrosa."),
    # --- 1.8 Marco normativo ---
    ("Este principio orienta la forma de plantear los ensayos: bajo control, con medidas de seguridad y con responsables definidos.",
     "Este principio orienta cómo se plantean los ensayos: bajo control y con responsables definidos."),
    ("consulta previa de restricciones, supervisión permanente del piloto y una misión clara y verificable.",
     "consulta previa de restricciones y supervisión permanente del piloto."),
    # --- Anexo E ---
    ("y los listados de los módulos principales.", "y los listados de los módulos principales. Los listados copian el código tal cual; solo se quitaron referencias internas de los comentarios."),
    # --- 1.9 Metodología ---
    ("Aquí el interés no es seleccionar alternativas, sino implementar y verificar que la cámara",
     "Aquí ya no se seleccionan alternativas: se implementa y se verifica que la cámara"),
    # --- 2.1 ---
    ("La matriz cumplió su función con la información disponible; lo que falló fue la calificación supuesta de la Raspberry Pi, que solo se pudo corregir midiendo.",
     "La matriz funcionó con la información que había; la calificación de la Raspberry Pi era una suposición y solo se pudo corregir midiendo."),
    ("En consecuencia, la ecuación integral que rige el parámetro de evasión del sistema se define como:",
     "Con esos tres términos, la distancia de seguridad es:"),
    ("Así, el LiDAR evita que la maniobra se active cuando el obstáculo todavía está lejos y sirve de respaldo cuando el sol deslumbra la cámara, porque su medida no depende de la imagen.", ""),
    # --- 2.2 ---
    (" Este apartado sigue el orden en que se trabajó: ensamble, conexiones, verificación en Mission Planner, validación del detector, despliegue en la computadora de a bordo, lógica de decisión y pruebas estáticas.", ""),
    ("En el cuerpo del documento solo se presentan la arquitectura (Figura 14) y los estados de la maniobra (Figura 15).",
     "Aquí se muestran la arquitectura (Figura 14) y los estados de la maniobra (Figura 15)."),
    # --- 2.3 ---
    ("Así la IA aporta criterio donde las reglas fijas son ineficientes, y las reglas responden donde la IA podría fallar.",
     "La IA decide en los casos ambiguos, donde las reglas fijas se equivocan más, y las reglas cubren los casos en que la IA podría fallar."),
    # --- 3 ---
    ("en la operación recomendada la ventaja de la IA es la eficiencia, no una seguridad mayor.",
     "en la operación recomendada la IA aporta eficiencia y no una seguridad adicional."),
    # --- 2.2.6: frases demasiado largas, y la entrada "detectada" que faltaba (son 15 en el código) ---
    ("De cada cuadro se calculan quince entradas para la IA 2: de la caja de YOLO, el alto, el ancho, el área, el ángulo horizontal y su variación, la confianza y el número de cuadros seguidos con detección; del LiDAR, la distancia y si la lectura es utilizable; de la Pixhawk, la velocidad que estima su filtro EKF; y de un seguimiento alfa-beta de la persona, la distancia, la velocidad de acercamiento, la velocidad lateral y el tiempo sin detección.",
     "De cada cuadro se calculan quince entradas para la IA 2. De la caja de YOLO salen si hay detección, el alto, el ancho, el área, el ángulo horizontal y su variación, la confianza y el número de cuadros seguidos con detección. El LiDAR aporta la distancia y si la lectura es utilizable, y la Pixhawk, la velocidad que estima su filtro EKF. Un seguimiento alfa-beta de la persona agrega la distancia, la velocidad de acercamiento, la velocidad lateral y el tiempo sin detección."),
    ("La salida del clasificador opera dentro de una envolvente de reglas que no puede saltar: (1) si el LiDAR mide menos de 3 m mientras el dron avanza, se detiene el avance sin importar lo que diga la IA; (2) el ascenso por una persona solo lo autoriza el árbitro de seguridad, cuando la persona está a menos de 3 m, o a menos de 8 m y acercándose; antes de eso la IA solo puede detener; (3) una salvaguarda geométrica detiene el dron si una persona seguida va a pasar a menos de 2 m en menos de 1.5 s; y (4) la parada de emergencia del radiocontrol (CH8) y el cambio de modo del piloto mandan siempre.",
     "La salida del clasificador opera dentro de una envolvente de reglas que la red no puede saltar. Primero, si el LiDAR mide menos de 3 m mientras el dron avanza, se detiene el avance sin importar lo que diga la IA. Segundo, el ascenso por una persona solo lo autoriza el árbitro de seguridad, cuando la persona está a menos de 3 m, o a menos de 8 m y acercándose; antes de eso la IA solo puede detener. Tercero, una salvaguarda geométrica detiene el dron si una persona seguida va a pasar a menos de 2 m en menos de 1.5 s. Cuarto, la parada de emergencia del radiocontrol (CH8) y el cambio de modo del piloto mandan siempre."),
]
