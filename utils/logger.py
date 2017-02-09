#!/usr/bin/env python

import logging
import os
import sys
try:
    import colorlog
    have_colorlog = True
except ImportError:
    have_colorlog = False

LOG_FILE_PATH = os.path.join(os.getcwd(), "LOG_FILE.log")
def get_logger(module_name):
    """
        module_name just to distinguish where the logs come from
    """
    # adding a new logging level
    logging.SUCCESS = 19   # as ALL = 0, DEBUG = 10, INFO = 20, WARN = 30, ERROR = 40, FATAL = CRITICAL, CRITICAL = 50
    logging.addLevelName(logging.SUCCESS, 'SUCCESS')
    logger = logging.getLogger(module_name)
    logger.success = lambda msg, *args: logger._log(logging.SUCCESS, msg, args)

    # colors
    if have_colorlog and os.isatty(2):
        format      = '[%(levelname)s] - %(message)s'
        colorformat = '%(log_color)s' + format
        console_log_formatter = colorlog.ColoredFormatter(colorformat,
        log_colors = { 'DEBUG'   : 'reset',       'INFO' : 'green',
                        'WARNING' : 'bold_yellow', 'ERROR': 'bold_red',
                        'CRITICAL': 'bold_red' })
    else:
    # create formatters
        console_log_formatter = logging.Formatter('[%(levelname)s] - %(message)s')
    file_log_formatter = logging.Formatter('%(asctime)s - %(name)s - [%(levelname)s] - %(message)s')

    #create file handler
    file_handler = logging.FileHandler(LOG_FILE_PATH)
    file_handler.setFormatter(file_log_formatter)
    file_handler.setLevel(logging.DEBUG)

    #create console log handler
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
