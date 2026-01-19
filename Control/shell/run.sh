#!/bin/bash

echo "Start ACW TTS-system"

cd ~/VAS/Control
source venv/bin/activate
python3 main.py
deactivate