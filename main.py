import pyrebase
import torch
from TTS.api import TTS
import simpleaudio as sa
import time
from pydub import AudioSegment
from pydub.playback import play
from dotenv import load_dotenv
import os

load_dotenv()

# device = "cuda" if torch.cuda.is_available() else "cpu"
USE_GPU = False

firebase_config = {
    "apiKey": os.getenv("FIREBASE_API_KEY"),
    "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
    "databaseURL": os.getenv("FIREBASE_DATABASE_URL"),
    "projectId": os.getenv("FIREBASE_PROJECT_ID"),
    "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
    "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID"),
    "appId": os.getenv("FIREBASE_APP_ID"),
    "measurementId": os.getenv("FIREBASE_MEASUREMENT_ID")
}

firebase = pyrebase.initialize_app(firebase_config)
db = firebase.database()
uid = "8e7e46ee-d2d6-4dcc-b757-8ff7a69b9585"
parameter_path = f"sound_machine/{uid}/parameter"

print("Loading TTS model, please wait...")
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=USE_GPU)
print("Model loaded.")

def run_sound(text_to_speak: str, model: str, volume: float=1.0, pitch: float=1.0, speed: float=1.0):
    volume = max(0.0, min(volume, 2.0))
    pitch = max(0.5, min(pitch, 2.0))
    speed = max(0.5, min(speed, 2.0))
    print(f"Generating voice {model} → pitch={pitch}, speed={speed}, volume={volume}")
    tts.tts_to_file(
        text=text_to_speak,
        speaker_wav=f"{model}.wav",
        language="en",
        speed=speed,
        file_path="output.wav"
    )
    audio = AudioSegment.from_file("output.wav")
    if pitch != 1.0:
        new_frame_rate = int(round(audio.frame_rate * pitch))
        audio = audio._spawn(audio.raw_data, overrides={'frame_rate': new_frame_rate})
        audio = audio.set_frame_rate(44100)
    audio = audio + (20 * (volume - 1))
    play(audio)
    print("Done playing voice.")

    
print("Listening for is_running = true ...")
while True:
    try:
        param = db.child(parameter_path).get().val()
        if param and param.get("is_running") == True:
            text_to_speak = param.get("text", "Hello world!")
            model_speech = param.get("model", "jokowi")
            print("is_running = True → executing TTS")
            try:
                volume = float(param.get("volume", 1.0))
                pitch  = float(param.get("pitch", 1.0))
                speed  = float(param.get("speed", 1.0))
            except ValueError:
                volume = 1.0
                pitch = 1.0
                speed = 1.0
            volume = max(0.0, min(volume, 2.0))
            pitch  = max(0.5, min(pitch, 2.0))
            speed  = max(0.5, min(speed, 2.0))
            run_sound(text_to_speak, model_speech, volume, pitch, speed)
            db.child(parameter_path).update({"is_running": False})
            print("is_running set to False")
        time.sleep(1)
    except KeyboardInterrupt:
        print("Stopped by user.")
        break
    except Exception as e:
        print("Error:", e)
        time.sleep(5)