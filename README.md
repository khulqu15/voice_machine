# Voice Machine TTS - Raspberry Pi Setup

This repository contains a Text-to-Speech (TTS) system designed to run on a Raspberry Pi. It uses gTTS for speech generation, with optional pitch, speed, and volume adjustments. An opening audio can be played before TTS output. Firebase is used for remote control.

This guide will help you set up the environment on Raspberry Pi for production-ready usage.

---

## 1. Update System

```bash
sudo apt update && sudo apt upgrade -y
```

---

## 2. Install Python 3.10 and pip

Raspberry Pi OS may not come with Python 3.10 by default.

```bash
sudo apt install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3.10-dev python3-pip
```

Verify installation:

```bash
python3.10 --version
pip3 --version
```

---

## 3. Create and Activate Virtual Environment

It is recommended to use a virtual environment to isolate dependencies.

```bash
python3.10 -m venv venv
source venv/bin/activate
```

To deactivate the virtual environment:

```bash
deactivate
```

---

## 4. Install Rust

Rust is required for certain audio libraries and performance optimizations.

```bash
curl https://sh.rustup.rs -sSf | sh
# Choose default installation (press 1)
source $HOME/.cargo/env
```

Verify Rust installation:

```bash
rustc --version
cargo --version
```

---

## 5. Install FFmpeg

FFmpeg is required for audio processing with pydub.

```bash
sudo apt update
sudo apt install -y ffmpeg
```

Verify FFmpeg installation:

```bash
ffmpeg -version
```

---

## 6. Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 7. Run the Voice Machine

1. Make sure your virtual environment is active:

```bash
source venv/bin/activate
```

2. Run the main script:

```bash
python main.py
```

3. The system will listen to Firebase parameters and play the opening audio followed by TTS.

---

## 8. Notes

* Ensure that the path to the opening audio is correct:

```text
./Control/assets/tts/opening.mp3
```

* Adjust volume, pitch, and speed parameters in Firebase for real-time control.
* Installing FFmpeg is mandatory for pydub to handle MP3/WAV audio properly.
* Rust is required if you are using TTS backends that rely on native libraries.

---

## 9. References

* [gTTS Documentation](https://gtts.readthedocs.io/en/latest/)
* [pydub Documentation](https://pydub.com/)
* [Firebase Python SDK](https://github.com/thisbejim/Pyrebase)
* [Rust Programming Language](https://www.rust-lang.org/)
* [FFmpeg Official](https://ffmpeg.org/)

---

## 10. License

This project is licensed under the Ninno Obayan License.
