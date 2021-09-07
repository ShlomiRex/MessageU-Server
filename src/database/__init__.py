import logging
import os
from defenitions import ROOT_DIR

DB_LOCATION = os.path.join(ROOT_DIR, "server.db")
MODULE_LOGGER_NAME = "Database"

format = '[ %(levelname)s ] %(asctime)s.%(msecs)03d - %(name)s - %(filename)s:%(lineno)s - %(funcName)s - %(message)s'
level = logging.DEBUG

logging.basicConfig(format=format, level=level, datefmt='%H:%M:%S')
