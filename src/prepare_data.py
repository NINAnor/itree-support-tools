import logging
import os


import src.decorators as dec
from src.config import load_catalog, load_parameters
from src.data import clean_data, load_data
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

    # get raw insitu fields based on municipality
    raw_insitu_fields = catalog["raw_in_situ_trees"]["fields"][municipality]
    logger.info(f"Raw insitu fields: {raw_insitu_fields}")

    # get nb list
    neighbourhood_list = au.get_neighbourhood_list(
        neighbourhood_path, neighbourhood_key
    )

    logger.info(f"Neighbourhood list: {neighbourhood_list}")

    # --- load data ---
    df_lookup = load_data.lookup(
        excel_path=catalog["lookup_species"]["filepath"],
        sheet_name=catalog["lookup_species"]["sheet_names"][0],
    )
    print(df_lookup.head())
    # load_data.stems(raw_in_situ, interim_input_stems)
    # load_data.crowns(raw_laser, interim_input_crowns)

    # --- clean data ---
    input_fc = os.path.join(
        interim_input_stems, catalog["interim_input_stems"]["fc"][0]
    )
    clean_data.create_schema(input_fc, df_lookup, municipality, raw_insitu_fields)


if __name__ == "__main__":
    """Load data from raw to interim."""

    # set up logger
    setup_logging()
    logger = logging.getLogger(__name__)

    # run function
    main()
