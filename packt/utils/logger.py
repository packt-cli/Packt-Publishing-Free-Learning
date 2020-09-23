#!/usr/bin/env python

import logging
import os
import sys


def get_logger(module_name, log_folder_path=os.getcwd()):
    """
        module_name just to distinguish where the logs come from
    """

    LOG_FILE_PATH = os.path.join(log_folder_path, "LOG_FILE.log")

    # adding a new logging level
    logging.SUCCESS = 19   # as ALL = 0, DEBUG = 10, INFO = 20, WARN = 30, ERROR = 40, FATAL = CRITICAL, CRITICAL = 50
    logging.addLevelName(logging.SUCCESS, 'SUCCESS')
    logger = logging.getLogger(module_name)
    logger.success = lambda msg, *args: logger._log(logging.SUCCESS, msg, args)

    # create formatters
    console_log_formatter = logging.Formatter('[%(levelname)s] - %(message)s')
    file_log_formatter = logging.Formatter('%(asctime)s - %(name)s - [%(levelname)s] - %(message)s')

    # create file handler
    file_handler = logging.FileHandler(LOG_FILE_PATH)
    file_handler.setFormatter(file_log_formatter)
    file_handler.setLevel(logging.DEBUG)

    # create console log handler
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(console_log_formatter)
    stream_handler.setLevel(logging.SUCCESS)

    logger.setLevel(logging.SUCCESS)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


if __name__ == "__main__":
    logger = get_logger('_this is me')
    logger.debug('This is debug level')
    logger.info('This is info level')
    logger.warning('This is warning level')
    logger.error('This is error level')
    logger.critical('This is critical level')
    logger.success('This is success level')
