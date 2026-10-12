---
name: cierre-sesion
description: Cierra una sesión de trabajo del proyecto del dron. Resume lo hecho, actualiza docs/ESTADO.md y docs/BITACORA.md, hace commit y hace push solo si Brahian confirma. Usar cuando diga "cerrar sesión", "guardar el avance" o "/cierre-sesion".
---

# Cierre de sesión

Brahian no es programador: explica cada paso en lenguaje sencillo, en español.

## Pasos

1. **Resumen.** Revisa lo que se hizo en la conversación y con `git status` y `git diff --stat`.
   Escribe un resumen corto: qué se hizo, qué quedó a medias y qué sigue.
2. **Revisa el estado real antes de escribir cifras.** Si hay un entrenamiento en marcha, lee
   `simulacion/modelos_master/estado_entrenamiento.json` (pasos, horas, nivel). No inventes números.
3. **Actualiza `docs/ESTADO.md`.** Cambia la fecha, el estado del entrenamiento, la sección Git y los
   pendientes. Mantén el archivo en **menos de 60 líneas**: borra lo que ya no es cierto.
4. **Actualiza `docs/BITACORA.md`.** Agrega una entrada nueva arriba, con la fecha de hoy y 3 a 6 viñetas.
   Si hubo una decisión de diseño, agrégala a `docs/DECISIONES.md` con su motivo.
5. **Escribe "proyecto de grado", no "tesis"**, en todos los textos nuevos.
6. **Mira qué se va a subir.** Ejecuta `git status --short` y `git add --dry-run .`. Avísale a Brahian si
   aparece algo que no debería estar: modelos `.zip` o `.pt`, `salida*/`, `.venv`, `.env`, claves, IPs.
   No cambies la lógica de ningún script.
7. **Haz el commit** (esto se puede deshacer): `git add .` y un mensaje en español, claro y específico,
   que termine con la línea de coautoría que indique el sistema.
8. **Pregunta antes del push.** Muestra qué rama y cuántos commits subirían, y pide confirmación
   explícita. Solo si responde que sí, ejecuta `git push` (con `-u origin <rama>` si es la primera vez).
   Si responde que no, deja el commit local y dilo.
9. **Cierra con un mensaje corto**: qué quedó guardado, qué no se subió y cuál es el siguiente paso.

## Reglas

- Nunca `git push --force`, nunca fusionar a `main` sin que Brahian lo pida, nunca borrar ramas ni etiquetas.
- Si el entrenamiento sigue corriendo, no muevas ni copies `modelos_master/ultimo.zip`.
- El repositorio es público: ni IPs, ni usuarios, ni contraseñas, ni claves.
