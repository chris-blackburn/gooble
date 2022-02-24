import logging

def getLogger():
    return logging.getLogger("gooble")

logger = getLogger()
logger.setLevel(logging.DEBUG)

sh = logging.StreamHandler()
sh.setLevel(logging.DEBUG)

formatter = logging.Formatter("[%(asctime)s]: %(levelname)s -> %(message)s")
sh.setFormatter(formatter)
logger.addHandler(sh)
