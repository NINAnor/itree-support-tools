import logging

import src.utils.decorators as dec
from extrapolation import clean_reference, clean_target
from src.config.logger import setup_logging


@dec.timer
def main():
    """Run main script."""
    df_ref = clean_reference.main()
    df_target = clean_target.main()

    return


if __name__ == "__main__":
    # set up logging
    setup_logging()
    logger = logging.getLogger(__name__)
    main()
