#!/bin/bash

echo "Start ACW TTS-system"

sudo docker run -d --name mongo -p 27017:27017 arm64v8/mongo:4.4.18
sudo pigpiod
cd ~/voice_machine/Control
source ~/voice_machine/venv/bin/activate
python3 main.py
deactivate