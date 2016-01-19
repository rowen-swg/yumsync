import os
import sys
import time

start = int(time.time())

def log(msg, header=False, log_dir=None):
    time_str = time.strftime('%Y-%m-%dT%X%z')
    delta = int(time.time()) - start
    m, s = divmod(delta, 60)
    h, m = divmod(m, 60)
    delta_str = '{:02d}:{:02d}:{:02d}'.format(h, m, s)

    output_str = "==> %s" % msg if header else msg

    if log_dir is not None:
        if os.path.exists(log_dir):
            with open(os.path.join(log_dir, 'sync.log'), 'a') as logfile:
                logfile.write('{} {}\n'.format(time_str, output_str))

    if not sys.__stdout__.isatty():
        sys.__stdout__.write('{} {}\n'.format(delta_str, output_str))
        sys.__stdout__.flush()

