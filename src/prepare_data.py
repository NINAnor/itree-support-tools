import logging
import os

import src.decorators as dec
from src.config import load_catalog, load_parameters
from src.data import clean, load
from src.logger import setup_logging
from src.utils import arcpy_utils as au


@dec.timer
def main():
    # load catalog

    logger = logging.getLogger(__name__)
    logger.info("Loading catalog...")
    catalog = load_catalog()
    logger.info("Loading parameters...")
    parameters = load_parameters()

    # set parameters
    municipality = parameters["municipality"]

    # load data
    neighbourhood_path = catalog["neighbourhood"]["filepath"]  # fc
    neighbourhood_key = catalog["neighbourhood"]["key"]  # field name

    raw_in_situ = catalog["raw_in_situ_trees"]["filepath"]  # filegdb
    raw_laser = catalog["raw_laser_trekroner"]["filepath"]  # filegdb
    interim_input_stems = catalog["interim_input_stems"]["filepath"]  # filegdb
    interim_input_crowns = catalog["interim_input_crowns"]["filepath"]  # filegdb

    interim_input_stems_fc = os.path.join(
        interim_input_stems, catalog["interim_input_stems"]["fc"][0]  # fc
    )

    raw_insitu_fields = catalog["raw_in_situ_trees"]["fields"][
        municipality
    ]  # [field names]

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
    df_lookup_fields = load.lookup_table(
        excel_path=catalog["lookup_fields"]["filepath"],
        sheet_name=catalog["lookup_fields"]["sheet_names"][3],
    )

    print(df_lookup_fields.head())

    df_lookup_species = load.lookup_table(
        excel_path=catalog["lookup_species"]["filepath"],
        sheet_name=catalog["lookup_species"]["sheet_names"][0],
    )
    print(df_lookup_species.head())
    load.copy_stems(raw_in_situ, interim_input_stems)
    load.copy_crowns(raw_laser, interim_input_crowns)

    # --- clean data ---

    clean.update_schema_stems(
        input_field_names=raw_insitu_fields,
        fc=interim_input_stems_fc,
        lookup_tb=df_lookup_fields,
        municipality=municipality,
    )


if __name__ == "__main__":
    """Load data from raw to interim."""

    # set up logger
    setup_logging()

    # run function
    main()
