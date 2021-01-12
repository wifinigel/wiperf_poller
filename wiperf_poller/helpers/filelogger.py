'''
A very simple file logging function based on Python native logging ,using
a rotating file handle to maintain file sizes
'''
from __future__ import print_function
import logging
import time
from logging.handlers import RotatingFileHandler

def FileLogger(log_file, error_log_file):
    '''
    A function to perform very simple logging to a named file. Any non-recoverable
    errors are written to stdout (e.g. can't open file)
    '''

    logger = logging.getLogger("Probe_Log")
    logger.setLevel(level=logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # add a rotating handler
    rot_handler = RotatingFileHandler(log_file, maxBytes=521000, backupCount=10)
    rot_handler.setFormatter(formatter)
    rot_handler.setLevel(level=logging.DEBUG)
    logger.addHandler(rot_handler)

    # add error logging file handler
    file_handler = logging.FileHandler(error_log_file, mode='w')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.ERROR)
    logger.addHandler(file_handler)

    return logger    
