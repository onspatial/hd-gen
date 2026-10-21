import time
import builtins
import warnings
import os
import datetime


def log(message):
    LOG_FILE_PATH = f"logs/{datetime.datetime.now().strftime('%Y%m%d')}/log.txt"
    os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)
    with open(LOG_FILE_PATH, "a") as log_file:
        log_file.write(f"{message}\n")

_original_print = builtins.print


def logger(args):
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    log(f"[{current_time}] {' '.join(map(str, args))}")


def print_time(*args, **kwargs):
    silence = kwargs.pop('silence', False)
    if silence:
        return
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    _original_print(f"[{current_time}]", *args, **kwargs)


def print_nothing(*args, **kwargs):
    silence = kwargs.pop('silence', True)
    no_log = kwargs.pop('no_log', True)
    if not no_log:
        logger(args)
    if not silence:
        print_time(*args, **kwargs)


def enable_timestamped_print():
    builtins.print = print_time


def disable():
    builtins.print = _original_print


def run():
    warnings.filterwarnings("ignore")
    enable_timestamped_print()


def enable_silence():
    warnings.filterwarnings("ignore")
    warnings.simplefilter("ignore")
    builtins.print = print_nothing


if __name__ == "__main__":
    enable_timestamped_print()

    print("This is a test message with timestamp.")

    disable()
    print("This is a test message without timestamp.")