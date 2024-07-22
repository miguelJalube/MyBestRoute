# log message to console and log file adding current function name
import inspect
import os


def log(msg, level='info'):
    if level == 'info':
        print(f'[INFO] {msg}')
    elif level == 'warning':
        print(f'[WARNING] {msg}')
    else:
        print(f'[ERROR]: {msg}')
    with open(os.getenv('LOG_FILE'), 'a') as f:
        f.write(f'[{level.upper()}] {msg}\n')
        f.write(f'Function: {inspect.stack()[1][3]}\n\n')
        f.close()
    return None
