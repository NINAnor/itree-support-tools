import logging
import os

import src.utils.decorators as dec
from src.config.logger import setup_logging
from extrapolation.nodes import pipeline


@dec.timer
def main():
    pipeline(reference_municipality="bodo")

    return


if __name__ == "__main__":
    # set up logging
    setup_logging()
    logger = logging.getLogger(__name__)
    main()
