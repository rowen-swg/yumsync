import os
import sys
import time
import logging

start = int(time.time())

def log(msg, header=False, log_dir=None, force=False):
    output_str = "==> %s" % msg if header else msg

    logging.info(output_str)
