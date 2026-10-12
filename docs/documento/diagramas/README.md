# Diagramas del documento

Cada diagrama tiene su fuente Mermaid (`.mmd`, se puede editar en https://mermaid.live) y su imagen (`.png`, lista para
pegar en Word). Todos son de autoría propia: según la plantilla USB no hace falta la nota "Elaboración propia".

| Archivo | En la copia intervenida | Qué muestra |
|---|---|---|
| `01_arquitectura` | Figura N2 (2.2.6) | Percepción (cámara, YOLO, LiDAR, EKF) → decisión (15 entradas, MLP, envolvente de reglas) → control (GUIDED, PSC/ATC); el piloto siempre manda |
| `02_estados` | Figura N3 (2.2.6) | Estados de la intervención: PILOTO, VIGILANDO, DETENER, DETENER Y ASCENDER, RETENIDO y PARADA |
| `03_experimento` | Figura N4 (2.3.1) | Secuencia de validación: simulación → banco → datos reales → modo sombra → vuelos → protocolo de campo |
| `04_porque_ia` | Figura N5 (2.3.3) | Reglas solas frente a IA con envolvente en los escenarios de discriminación |
| `05_metodologia_corregida.png` | Reemplaza a la Figura 16 (1.9.3) | La misma figura original con dos textos corregidos: "computadora de a bordo" y "entorno exterior" en vez de "Raspberry Pi" y "entorno indoor" |

Para regenerar las imágenes (necesita Node y el navegador Chromium):

```
npx -y @mermaid-js/mermaid-cli@11.4.2 -i 01_arquitectura.mmd -o 01_arquitectura.png -s 3 -b white
```

`03_experimento` se genera con `-w 1600 -s 2` para que salga en una sola fila.
