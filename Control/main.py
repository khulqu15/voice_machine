import asyncio
import time as tm
import configparser
import sys
import pygame
from src.local_message import LocalMessage
from src.logger import Logger
import os


if __name__ == '__main__':
    pygame.mixer.pre_init(frequency=48000, buffer=2048)
    pygame.mixer.init()

    config = configparser.ConfigParser()
    config_file = 'vas.config'
    config.read(config_file)

    lm=LocalMessage()

    Logger.info("Voice Alarm Device Control is ON")
    lm.main_run()
