import logging

from .consumer import *
from .producer import *

__all__ = consumer.__all__ + producer.__all__


LOG_FORMAT = "%(levelname) -10s %(asctime)s %(name) -30s %(funcName) " "-15s %(lineno) -5d: %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
