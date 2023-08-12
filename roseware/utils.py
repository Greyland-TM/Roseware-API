## Logging Imports
import logging
import os

### LOGGING ###


def make_logger(
    name,
    stream=False,
    file_name="logs/general.log",
    log_level=logging.DEBUG,
    set_propagate=True,
):
    logs_dir = 'logs'
    
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    formatter = logging.Formatter(
        "[%(asctime)s] [%(name)s] [%(levelname)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if stream:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    if os.path.exists(logs_dir):
        error_handler = logging.FileHandler(f"{logs_dir}/errors.log")
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)

        file_handler = logging.FileHandler(file_name)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    else:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        logger.warning(f"'{logs_dir}' directory does not exist. Create one to start logging.")

    logger.propagate = set_propagate

    return logger


### END LOGGING ###
