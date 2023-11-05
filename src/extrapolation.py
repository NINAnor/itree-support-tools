import logging

import src.utils.decorators as dec
from extrapolation.nodes import pipeline
from src.config.logger import setup_logging


@dec.timer
def main():
    pipeline(reference_municipality="oslo")

    return


if __name__ == "__main__":
    # set up logging
    setup_logging()
    logger = logging.getLogger(__name__)
    main()
