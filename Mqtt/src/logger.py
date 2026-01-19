import logging
from logging.handlers import TimedRotatingFileHandler
import os
from datetime import datetime
import pytz

class Logger:
    _instance = None
    _log_directory = 'logs'
    _timezone = pytz.timezone('Asia/Bangkok')  # GMT+7

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if not os.path.exists(self._log_directory):
            os.makedirs(self._log_directory)

        log_file = os.path.join(self._log_directory, f'mqtt_{self._get_current_time().strftime("%Y-%m-%d")}.log')
        self.logger = logging.getLogger('ApplicationLogger')
        self.logger.setLevel(logging.DEBUG)

        # # Create a TimedRotatingFileHandler
        # handler = TimedRotatingFileHandler(log_file, when="midnight", interval=1, backupCount=7)
        # handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        # self.logger.addHandler(handler)
        # Hanya tambahkan handler jika belum ada
        if not self.logger.handlers:
            handler = TimedRotatingFileHandler(
                log_file, when="midnight", interval=1, backupCount=7
            )
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            ))
            self.logger.addHandler(handler)

    def _get_current_time(self):
        return datetime.now(self._timezone)

    @classmethod
    def debug(cls, message):
        cls.get_instance().logger.debug(message)

    @classmethod
    def info(cls, message):
        cls.get_instance().logger.info(message)

    @classmethod
    def warning(cls, message):
        cls.get_instance().logger.warning(message)

    @classmethod
    def error(cls, message):
        cls.get_instance().logger.error(message)

    @classmethod
    def critical(cls, message):
        cls.get_instance().logger.critical(message)