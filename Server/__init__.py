import logging

LOGGER_FORMAT = '[ %(levelname)s ] %(asctime)s.%(msecs)03d - %(filename)s:%(lineno)s - %(funcName)s - %(message)s'
LOGGER_FORMAT_THREAD = '[ %(levelname)s ] %(asctime)s.%(msecs)03d - [Thread %(thread)d] - %(filename)s:%(lineno)s - %(funcName)s - %(message)s'
LOGGER_DATE_FORMAT = '%H:%M:%S'
LOGGER_DEFAULT_LEVEL = logging.DEBUG
logging.basicConfig(format=LOGGER_FORMAT, level=LOGGER_DEFAULT_LEVEL, datefmt=LOGGER_DATE_FORMAT)
