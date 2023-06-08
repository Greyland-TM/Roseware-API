import logging


def make_logger():
    # check if logger is already created
    logger = logging.getLogger(__name__)
    if not logger.handlers:
        # set up logger
        logger.setLevel(logging.DEBUG)
        
        # add stream handler to log to console
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        logger.addHandler(ch)

        # add file handler to log to file
        fh = logging.FileHandler('roseware.log')
        fh.setLevel(logging.DEBUG)
        logger.addHandler(fh)

    return logger