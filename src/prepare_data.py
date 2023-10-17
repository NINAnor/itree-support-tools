import logging
import os

import arcpy

import src.decorators as dec
from src.config import load_catalog, load_parameters
from src.data import load_data
from src.logger import setup_logging
from src.utils import arcpy_utils as au


@dec.timer
def main():
    # load catalog
    logger.info("Loading catalog...")
    catalog = load_catalog()
    logger.info("Loading parameters...")
    parameters = load_parameters()

    # set parameters
    municipality = parameters["municipality"]

    # load data
    neighbourhood_path = catalog["neighbourhood"]["filepath"]
    neighbourhood_key = catalog["neighbourhood"]["key"]

    raw_in_situ = catalog["raw_in_situ_trees"]["filepath"]
    raw_laser = catalog["raw_laser_trekroner"]["filepath"]

    interim_input_stems = catalog["interim_input_stems"]["filepath"]
    interim_input_crowns = catalog["interim_input_crowns"]["filepath"]

    # confirm municipality
    confirm_municipality = (
        input(f"Is '{municipality}' the correct municipality? (y/n): ").strip().lower()
    )
    if confirm_municipality != "y":
        logger.info("User disagreed with the municipality.")
        exit()

    # get nb list
    neighbourhood_list = au.get_neighbourhood_list(
        neighbourhood_path, neighbourhood_key
    )

    logger.info(f"Neighbourhood list: {neighbourhood_list}")

    # --- load data ---
    load_data.stems(raw_in_situ, interim_input_stems)
    load_data.crowns(raw_laser, interim_input_crowns)


if __name__ == "__main__":
    """Load data from raw to interim."""

    # set up logger
    setup_logging()
    logger = logging.getLogger(__name__)

    # run function
    main()
