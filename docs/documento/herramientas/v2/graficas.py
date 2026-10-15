"""Gráficas del capítulo 3 con la misma letra y colores que los diagramas. Uso: python graficas.py CARPETA_SALIDA"""
import re
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from datos_tablas import DEGRADADAS, VELOCIDADES

plt.rcParams.update({'font.family': ['Liberation Serif'], 'font.size': 10,
                     'axes.edgecolor': '#44546A', 'axes.labelcolor': 'black', 'xtick.color': 'black',
                     'ytick.color': 'black', 'axes.spines.top': False, 'axes.spines.right': False})
C_REGLAS, C_IA = '#9DB7D5', '#44546A'
OUT = sys.argv[1]
W = 15.5 / 2.54


def barras(ax, etiquetas, a, b, horizontal=False, titulo_a='Reglas solas', titulo_b='IA con reglas', fmt='{:.0f}'):
    n = len(etiquetas)
    ancho = 0.38
    pos = list(range(n))
    if horizontal:
        r1 = ax.barh([p - ancho / 2 for p in pos], a, ancho, color=C_REGLAS, edgecolor='#44546A', label=titulo_a)
        r2 = ax.barh([p + ancho / 2 for p in pos], b, ancho, color=C_IA, edgecolor='#44546A', label=titulo_b)
        ax.set_yticks(pos)
        ax.set_yticklabels(etiquetas)
        ax.invert_yaxis()
    else:
        r1 = ax.bar([p - ancho / 2 for p in pos], a, ancho, color=C_REGLAS, edgecolor='#44546A', label=titulo_a)
        r2 = ax.bar([p + ancho / 2 for p in pos], b, ancho, color=C_IA, edgecolor='#44546A', label=titulo_b)
        ax.set_xticks(pos)
        ax.set_xticklabels(etiquetas)
    for rs in (r1, r2):
        ax.bar_label(rs, labels=[fmt.format(v.get_width() if horizontal else v.get_height()) for v in rs], padding=2,
                     fontsize=9)


# G1: discriminación
fig, ax = plt.subplots(figsize=(W, 7.2 / 2.54 * 1.1))
et = ['Cruza 3–4 m por delante', 'Cruza justo por donde pasa', 'De frente a 3 m del costado',
      'De frente a 1 m del costado', 'Camina delante, más rápido', 'Total (500 vuelos)']
barras(ax, et, [95, 65, 96, 100, 100, 91.2], [98, 77, 95, 100, 100, 94.0], horizontal=True, fmt='{:g} %')
ax.set_xlim(0, 118)
ax.set_xlabel('Vuelos con decisión correcta (%)')
ax.legend(loc='upper center', bbox_to_anchor=(0.5, 1.13), ncol=2, frameon=False)
fig.tight_layout()
fig.savefig(f'{OUT}/g1_discriminacion.png', dpi=300)

# G2: 3840 vuelos
fig, ax = plt.subplots(figsize=(W, 6.2 / 2.54 * 1.1))
barras(ax, ['Persona a < 2 m\nbajo 3.30 m', 'Activaciones\ninnecesarias', 'Riesgos\nno evitados', 'Choques'],
       [420, 137, 92, 39], [218, 67, 67, 28])
ax.set_ylabel('Vuelos (de 3840)')
ax.legend(frameon=False)
fig.tight_layout()
fig.savefig(f'{OUT}/g2_mundos.png', dpi=300)

# G3: condiciones degradadas
cond, reg, ia = [], [], []
for fila in DEGRADADAS[1:]:
    cond.append(fila[0].split(' ')[0])
    reg.append(float(re.match(r'([\d.]+) %', fila[1]).group(1)))
    ia.append(float(re.match(r'([\d.]+) %', fila[2]).group(1)))
fig, ax = plt.subplots(figsize=(W, 6.4 / 2.54 * 1.1))
barras(ax, cond, reg, ia, fmt='{:.1f}')
ax.set_ylim(94, 99.5)
ax.set_ylabel('Éxito (%)')
ax.legend(frameon=False, ncol=2, loc='upper right')
for t in ax.texts:
    t.set_fontsize(6.5)
    t.set_rotation(90)
fig.tight_layout()
fig.savefig(f'{OUT}/g3_degradadas.png', dpi=300)

# G4: velocidad máxima segura
cond = [f[0].split(' ')[0] for f in VELOCIDADES[1:]]
fig, ax = plt.subplots(figsize=(W, 6.4 / 2.54 * 1.1))
n = len(cond)
ancho = 0.26
cols = [('Panel fijo', '#DCE6F1', 1), ('Persona quieta', '#9DB7D5', 2), ('Persona que corre', '#44546A', 3)]
for k, (nombre, color, j) in enumerate(cols):
    vals = [float(f[j]) for f in VELOCIDADES[1:]]
    rs = ax.bar([p + (k - 1) * ancho for p in range(n)], vals, ancho, color=color, edgecolor='#44546A', label=nombre)
    ax.bar_label(rs, labels=['%g' % v for v in vals], padding=2, fontsize=8)
ax.set_xticks(range(n))
ax.set_xticklabels(cond)
ax.set_ylabel('Velocidad máxima segura (m/s)')
ax.set_ylim(0, 13.5)
ax.legend(frameon=False, ncol=3, loc='upper center')
fig.tight_layout()
fig.savefig(f'{OUT}/g4_velocidades.png', dpi=300)
print('ok')
