import logging
import os

import src.decorators as dec
from src.config import load_catalog, load_parameters
from src.integration import case_2_voronoi as voronoi
from src.integration import case_3_model_crown as model_crown
from src.integration import classify_geo_relation as cgr
from src.integration import merge_trees
from src.logger import setup_logging
from src.utils import arcpy_utils as au


@dec.timer
def join_data(round):
    """_summary_

    Parameters
    ----------
    round : int
        Round 1 (process per neighbourhood) or Round 2 (process whole study area)
    """
    # load catalog

    logger = logging.getLogger(__name__)
    logger.info("Loading catalog...")
    catalog = load_catalog()
    logger.info("Loading parameters...")
    parameters = load_parameters()

    # set parameters
    municipality = parameters["municipality"]
    spatial_reference = parameters["spatial_reference"][municipality]

    # load data
    gdb_admin = catalog["admin"]["filepath"]
    fc_area_extent = os.path.join(gdb_admin, catalog["admin"]["fc"][4])
    fc_neighbourhood = catalog["neighbourhood"]["filepath"]
    key_neighbourhood = catalog["neighbourhood"]["key"]  # field name

    # input
    gdb_interim_input_stems = catalog["interim_input_stems"]["filepath"]
    gdb_interim_input_crowns = catalog["interim_input_crowns"]["filepath"]
    fc_interim_input_stems = os.path.join(
        gdb_interim_input_stems, catalog["interim_input_stems"]["fc"][0]
    )

    # interim
    gdb_crowns_round_1 = catalog["geo_relation_round_1"]["filepath"]
    fc_crowns_round_1 = os.path.join(
        gdb_crowns_round_1, catalog["geo_relation_round_1"]["fc"][0]
    )
    gdb_crowns_round_2 = catalog["geo_relation_round_2"]["filepath"]

    # confirm municipality
    if round == 1:
        confirm_municipality = (
            input(f"Is '{municipality}' the correct municipality? (y/n): ")
            .strip()
            .lower()
        )
        if confirm_municipality != "y":
            logger.info("User disagreed with the municipality.")
            exit()

    # get nb list
    ls_neighbourhood = au.get_neighbourhood_list(fc_neighbourhood, key_neighbourhood)

    # test neighbourhood bærum
    ls_neighbourhood = ["302420", "302421", "302422"]
    logger.info(f"Neighbourhood list: {ls_neighbourhood}")

    if round == 1:
        logger.info("\n\nSTARTING ROUND 1 (PER NEIGHBOURHOOD) .....\n")
        # 1. CLASSIFY geo relation per neighbourhood (round = 1)
        cgr.classify_per_nb(
            ls_neighbourhood,
            gdb_interim_input_crowns,
            gdb_interim_input_stems,
            spatial_reference,
            round,
        )

        # 2. VORONOI  tesselation to split "CASE 2" crowns
        voronoi.split_per_nb(
            gdb_interim_input_stems,
            ls_neighbourhood,
            municipality,
            spatial_reference,
            round,
            fc_area_extent,
        )

        # 3. MODEL use a buffer based on in-situ radius to model "CASE 3" crowns
        model_crown.buffer_per_nb(
            ls_neighbourhood, gdb_interim_input_stems, spatial_reference, municipality
        )

        # 4. MERGE  case 1, split case 2 and modelled case 3 crowns
        merge_trees.merge_per_nb(
            ls_neighbourhood, gdb_interim_input_stems, spatial_reference, round
        )

        # MERGE  AND CLEAN ROUND I
        merge_trees.merge_study_area(gdb_crowns_round_1, fc_crowns_round_1)
        merge_trees.clean(fc_crowns_round_1)
    elif round == 2:
        logger.info("\n\nSTARTING ROUND 2 (STUDY AREA).....\n")
        # 1. CLASSIFY geo relation
        cgr.classify_study_area(
            fc_crowns_round_1,
            fc_interim_input_stems,
            gdb_crowns_round_2,
            spatial_reference,
            round,
        )

        # 2. VORONOI  tesselation to split "CASE 2" crowns
        voronoi.split_study_area(
            gdb_crowns_round_2,
            fc_interim_input_stems,
            spatial_reference,
            fc_area_extent,
        )

        # 3. MODEL use a buffer based on in-situ radius to model "CASE 3" crowns
        model_crown.buffer_study_area(
            gdb_crowns_round_2, fc_crowns_round_1, spatial_reference, municipality
        )


@dec.timer
def merge_data():
    """_summary_"""
    logger = logging.getLogger(__name__)
    logger.info("Loading catalog...")
    catalog = load_catalog()

    gdb_crowns_round_2 = catalog["geo_relation_round_2"]["filepath"]
    # feature classes
    fc_crowns_in_situ = os.path.join(
        gdb_crowns_round_2, catalog["geo_relation_round_2"]["fc"][0]
    )
    fc_all_crowns = os.path.join(
        gdb_crowns_round_2, catalog["geo_relation_round_2"]["fc"][1]
    )
    merge_trees.merge_complete(gdb_crowns_round_2, fc_crowns_in_situ, fc_all_crowns)
    merge_trees.clean(fc_crowns_in_situ)
    merge_trees.clean(fc_all_crowns)


# TODO
# CREATE FUNCTION TO SELECT TOPS WITHIN CROWNS


@dec.timer
def copy_output():
    """Copy output features to interim/geo_relation.gdb"""
    logger = logging.getLogger(__name__)
    logger.info("Loading catalog...")
    catalog = load_catalog()

    # input
    gdb_crowns_round_2 = catalog["geo_relation_round_2"]["filepath"]
    # feature classes
    fc_crowns_in_situ = os.path.join(
        gdb_crowns_round_2, catalog["geo_relation_round_2"]["fc"][0]
    )
    fc_all_crowns = os.path.join(
        gdb_crowns_round_2, catalog["geo_relation_round_2"]["fc"][1]
    )
    gdb_input_stems = catalog["interim_input_stems"]["filepath"]
    fc_input_stems = os.path.join(
        gdb_input_stems, catalog["interim_input_stems"]["fc"][0]
    )

    # output
    gdb_geo_relation = catalog["geo_relation"]["filepath"]
    # feature classes
    fc_crowns_in_situ_output = os.path.join(
        gdb_geo_relation, catalog["geo_relation"]["fc"][0]
    )
    fc_crowns_all_output = os.path.join(
        gdb_geo_relation, catalog["geo_relation"]["fc"][1]
    )
    fc_output_stems = os.path.join(gdb_geo_relation, catalog["geo_relation"]["fc"][2])

    # copy
    import arcpy

    au.createGDB_ifNotExists(gdb_geo_relation)
    logger.info("Copying results to geo_relation.gdb...")
    arcpy.CopyFeatures_management(fc_crowns_in_situ, fc_crowns_in_situ_output)
    arcpy.CopyFeatures_management(fc_all_crowns, fc_crowns_all_output)
    arcpy.CopyFeatures_management(fc_input_stems, fc_output_stems)


if __name__ == "__main__":
    """Load data from raw to interim."""

    # set up logger
    setup_logging()

    # run script
    n_rounds = (1, 2)
    # input(
    #    "Close any ArcGIS Pro Instances before running this code! Press Enter to continue..."
    # )

    # two rounds of point and polygon matching
    # round 1: per neighbourhood
    # round 2: whole study area (control, to check if trees on the border of neighbourhoods are correctly matched)
    for counter in n_rounds:
        join_data(round=counter)

    # merge crowns in-situ and all crowns
    merge_data()
    # copy output to geo_relation.gdb
    copy_output()

    # prepare for attribute computation
    # TODO automate pre-processing

    # input("Check if stem layer contains XY coord. Press Enter to continue...")
    # input("MANUALLY Join stem to crown (one-to-one, contains, join_count = 1))")
    # check if crown contains stem attr.

    # Step 1 Overla analaysis
    # subroutine overlay_attributes.py
