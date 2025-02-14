# Description: This file contains the logging manager.
import logging

class LoggingManager:
    def __init__(self, log_file):
        logging.basicConfig(filename=log_file, level=logging.INFO)

    def log(self, message):
        logging.info(message)