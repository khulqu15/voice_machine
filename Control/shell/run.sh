#!/bin/bash

echo "Start ACW TTS-system"

docker start mongo || true
cd ~/voice_machine/Control
source ~/voice_machine/venv/bin/activate
python3 main.py
deactivate