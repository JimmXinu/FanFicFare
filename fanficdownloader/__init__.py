# -*- coding: utf-8 -*-

try:
    # just a way to switch between web service and CLI/PI
    import google.appengine.api 
except:
    import sys
    if sys.version_info >= (2, 7):
        import logging
        logger = logging.getLogger(__name__)
        loghandler=logging.StreamHandler()
        loghandler.setFormatter(logging.Formatter("FFDL:%(levelname)s:%(filename)s(%(lineno)d):%(message)s"))
        logger.addHandler(loghandler)
        loghandler.setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)

