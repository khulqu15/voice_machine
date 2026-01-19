import multiprocessing
from gtts import gTTS
import pigpio as pi
import asyncio
import pygame
from time import sleep
import os

from .files import *

class Speech:
    def __init__(self):
        self.restart = False
        self.cnt = 0
        create_folder('_temp')

    def __clean_sentence(self, sentence):
        sentence = sentence.lower()
        cleaned_sentence = ''.join(char for char in sentence if char.isalnum())
        return cleaned_sentence


    # Play a music file using pygame mixer.
    def __play(self, filename:str, restart:bool = False, delete_file:bool = True):
        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()
        if restart:
            while pygame.mixer.music.get_busy():
                continue
        else:
            self.wait_free()
        # if delete_file:
        #     os.remove(filename)
    
    # Turn the system on. Plays an audio file indicating the system is on.
    def system_on(self):
        sleep(1)

        _filename = 'assets/tts/systemon.mp3'
        pygame.mixer.music.load(_filename)
        pygame.mixer.music.play()
        
        self.wait_free()

    # Generates text-to-speech audio from the input text in the specified language.
    def text_to_speech(self, text, lang = 'id') -> bool:
        convertStr = self.__clean_sentence(text)
        _filename = f'_temp/{convertStr}.mp3'
        if not os.path.exists(_filename):
            tts = gTTS(text=text, lang=lang)
            try:
                tts.save(_filename)
            except:
                return False

        
        self.wait_free()
        
        pygame.mixer.music.load('assets/tts/opening.mp3')
        pygame.mixer.music.play()
        self.wait_free()

        self.__play(_filename)
        return True
    
    # Waits for the pygame mixer to finish playing music. It checks for an interrupt button press and stops the music and restarts the voice if needed.
    def wait_free(self):
        _cnt = 1000
        while pygame.mixer.music.get_busy():
            _cnt -= 1
            if _cnt <= 0:
                _cnt = 1000
    
    # Plays an alarm sound.
    def play_alarm(self, path):

        self.wait_free()

        pygame.mixer.music.load(path)
        pygame.mixer.music.play()

        self.wait_free()
    
    # Return the status of whether the pygame mixer music is currently playing or paused.
    def status(self):
        return pygame.mixer.music.get_busy()
