#!/bin/bash
# Arranca (o reinicia) el visor web de la cámara en segundo plano. Opciones: --lado-a-lado, --yolo original|corregida
pkill -f "python -u visor_web.py"
sleep 1
cd ~/Escritorio/dron_ia
setsid nohup ~/dron_env/bin/python -u visor_web.py "$@" > ~/visor.log 2>&1 < /dev/null &
echo "visor arrancado $* (log en ~/visor.log)"
