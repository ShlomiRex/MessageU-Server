import logging

format = '[ %(levelname)s ] %(asctime)s.%(msecs)03d - %(filename)s:%(lineno)s - %(funcName)s - %(message)s'
thread_format = '[ %(levelname)s ] %(asctime)s.%(msecs)03d - [Thread %(thread)d] - %(filename)s:%(lineno)s - %(funcName)s - %(message)s'
level = logging.DEBUG
logging.basicConfig(format=format, level=level, datefmt='%H:%M:%S')
