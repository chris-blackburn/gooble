#!/usr/bin/env python3

import os
import sys

from . import Gooble

from .logs import getLogger
logger = getLogger()

if __name__=="__main__":
    logger.info("Welcome to gooble")
    token = os.getenv("TOKEN")
    if not token:
        logger.error("Please set the TOKEN environment variable")
        sys.exit(1)

    gooble = Gooble()
    gooble.run(token)
