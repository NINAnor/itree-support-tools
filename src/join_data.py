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
    fc_crowns_round_2 = os.path.join(
        gdb_crowns_round_2, catalog["geo_relation_round_2"]["fc"][0]
    )

    fc_all_crowns = os.path.join(
        gdb_crowns_round_2, catalog["geo_relation_round_2"]["fc"][1]
    )

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
    ls_neighbourhood = ["302401", "302402"]
    logger.info(f"Neighbourhood list: {ls_neighbourhood}")

    # 1. CLASSIFY geo relation
    if round == 1:
        logger.info("STARTING ROUND 1 .....")
        cgr.main(
            ls_neighbourhood,
            gdb_interim_input_crowns,
            gdb_interim_input_stems,
            spatial_reference,
            round,
        )

        # 2. VORONOI  tesselation to split "CASE 2" crowns
        voronoi.main(
            gdb_interim_input_stems,
            ls_neighbourhood,
            municipality,
            spatial_reference,
            round,
        )

        # 3. MODEL use a buffer based on in-situ radius to model "CASE 3" crowns
        model_crown.main(
            ls_neighbourhood, gdb_interim_input_stems, spatial_reference, municipality
        )

        # 4. MERGE  case 1, split case 2 and modelled case 3 crowns
        merge_trees.part_1(
            ls_neighbourhood, gdb_interim_input_stems, spatial_reference, round
        )

        # MERGE  AND CLEAN ROUND I
        merge_trees.part_2(gdb_crowns_round_1)
        merge_trees.clean(fc_crowns_round_1)
    elif round == 2:
        logger.info("STARTING ROUND 2 .....")
        # 1. CLASSIFY geo relation
        cgr.all(
            fc_crowns_round_1,
            fc_interim_input_stems,
            gdb_crowns_round_2,
            spatial_reference,
            round,
        )

        # 2. VORONOI  tesselation to split "CASE 2" crowns
        voronoi.all(gdb_crowns_round_2, fc_interim_input_stems, spatial_reference)

        # 3. MODEL use a buffer based on in-situ radius to model "CASE 3" crowns
        model_crown.all(
            gdb_crowns_round_2, fc_crowns_round_1, spatial_reference, municipality
        )


def merge_data():
    logger = logging.getLogger(__name__)
    logger.info("Loading catalog...")
    catalog = load_catalog()

    gdb_crowns_round_2 = catalog["geo_relation_round_2"]["filepath"]
    fc_crowns_round_2 = os.path.join(
        gdb_crowns_round_2, catalog["geo_relation_round_2"]["fc"][0]
    )

    fc_all_crowns = os.path.join(
        gdb_crowns_round_2, catalog["geo_relation_round_2"]["fc"][1]
    )
    merge_trees.part_3(gdb_crowns_round_2, fc_crowns_round_2, fc_all_crowns)
    merge_trees.clean(fc_crowns_round_2)


if __name__ == "__main__":
    """Load data from raw to interim."""

    # set up logger
    setup_logging()

    # run script
    n_rounds = (1, 2)

    # two rounds of point and polygon matching
    for counter in n_rounds:
        join_data(round=counter)

    # merge results from round 1 and 2 into:
    # merge_round_2.gdb/crowns_in_situ
    # merge_round_2.gdb/all_crowns
    merge_data()

    ##TODO
    # git commit
    # test merge c4
    # move to VDI
    # run for all nb
