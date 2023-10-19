# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------- #
# Name: prepare_data.py
# Date: 2023-10-19
# Description: Prepare data for itree-eco analysis and extrapolation
# Author: Willeke A'Campo
# Dependencies: ArcGIS Pro 3.0+, Spatial Analyst
# --------------------------------------------------------------------------- #

import logging
import os

import src.utils.decorators as dec
from src.config.config import load_catalog, load_parameters
from src.config.logger import setup_logging
from src.data import clean, load
from src.utils import arcpy_utils as au


@dec.timer
def prepare_data():
    # load catalog

    logger = logging.getLogger(__name__)
    logger.info("Loading catalog...")
    catalog = load_catalog()
    logger.info("Loading parameters...")
    parameters = load_parameters()

    # set parameters
    municipality = parameters["municipality"]

    # load data
    fc_neighbourhood = catalog["neighbourhood"]["filepath"]
    key_neighbourhood = catalog["neighbourhood"]["key"]  # field name

    fc_raw_in_situ = catalog["raw_in_situ_trees"]["filepath"]
    fc_raw_laser = catalog["raw_laser_trekroner"]["filepath"]

    gdb_interim_input_stems = catalog["interim_input_stems"]["filepath"]
    gdb_interim_input_crowns = catalog["interim_input_crowns"]["filepath"]

    fc_interim_input_stems = os.path.join(
        gdb_interim_input_stems, catalog["interim_input_stems"]["fc"][0]
    )

    ls_raw_insitu_fields = catalog["raw_in_situ_trees"]["fields"][
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
    ls_neighbourhood = au.get_neighbourhood_list(fc_neighbourhood, key_neighbourhood)

    logger.info(f"Neighbourhood list: {ls_neighbourhood}")

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
    load.copy_stems(fc_raw_in_situ, gdb_interim_input_stems)
    load.copy_crowns(fc_raw_laser, gdb_interim_input_crowns)

    # --- clean data ---
    clean.update_schema_stems(
        input_field_list=ls_raw_insitu_fields,
        input_fc=fc_interim_input_stems,
        lookup_df=df_lookup_fields,
        municipality=municipality,
    )

    clean.fill_attributes(
        input_gdb=gdb_interim_input_stems,
        input_fc=fc_interim_input_stems,
        lookup_excel=catalog["lookup_species"]["filepath"],
        lookup_sheet=catalog["lookup_species"]["sheet_names"][0],
    )

    clean.group_by_neighbourhood(
        point_fc=fc_interim_input_stems,
        polygon_fc=fc_neighbourhood,
        selecting_key=key_neighbourhood,
        output_gdb=gdb_interim_input_stems,
        output_key="stem_id",
    )


if __name__ == "__main__":
    """Load data from raw to interim."""

    # set up logger
    setup_logging()

    # run script
    prepare_data()

# --------------------------------------------------------------------------- #
