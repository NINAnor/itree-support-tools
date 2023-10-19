# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------- #
# Name: join_data.py
# Date: 2023-10-19
# Description: Ensure that stems are correctly matched to crowns
# Author: Willeke A'Campo
# Dependencies: ArcGIS Pro 3+, Spatial Analyst Extension
# --------------------------------------------------------------------------- #

import logging
import os

import src.utils.decorators as dec
from src.config.config import load_catalog, load_parameters
from src.integration import case_2_voronoi as voronoi
from src.integration import case_3_model_crown as model_crown
from src.integration import classify_geo_relation as cgr
from src.integration import merge_trees
from src.config.logger import setup_logging
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

    # clean
    fields_to_keep = [
        "OBJECTID",
        "SHAPE",
        "Shape_Length",
        "Shape_Area",
        "geo_relation",
        "tree_height_laser",
        "tree_altit",
    ]

    au.keep_fields(input_fc=fc_crowns_in_situ_output, fields_to_keep=fields_to_keep)
    au.keep_fields(input_fc=fc_crowns_all_output, fields_to_keep=fields_to_keep)


def quality_check():
    """Check if crowns are correctly matched to stems"""
    logger = logging.getLogger(__name__)
    logger.info("Loading catalog...")
    catalog = load_catalog()
    parameters = load_parameters()

    # input
    municipality = parameters["municipality"]
    gdb_geo_relation = catalog["geo_relation"]["filepath"]
    # feature classes
    fc_crowns = os.path.join(gdb_geo_relation, catalog["geo_relation"]["fc"][1])
    fc_stems = os.path.join(gdb_geo_relation, catalog["geo_relation"]["fc"][2])

    # output
    fc_output = os.path.join(gdb_geo_relation, catalog["geo_relation"]["fc"][4])

    # check if crowns are correctly matched to stems
    import arcpy

    arcpy.MakeFeatureLayer_management(fc_crowns, "crowns_lyr")
    arcpy.MakeFeatureLayer_management(fc_stems, "stems_lyr")
    arcpy.SelectLayerByLocation_management("crowns_lyr", "CONTAINS", "stems_lyr")

    count_crowns = int(arcpy.GetCount_management("crowns_lyr").getOutput(0))
    count_stems = int(arcpy.GetCount_management("stems_lyr").getOutput(0))

    if count_crowns == count_stems:
        logger.info(
            f"All stems (n= {count_stems}) are correctly matched to crowns (n= {count_crowns})"
        )

        return True
    else:
        logger.error(
            f"WARNING: {count_stems - count_crowns} stems are not matched to crowns"
        )
        logger.error("Check crowns and stems in ArcGIS Pro.")

    # Clear Selection
    arcpy.SelectLayerByAttribute_management("crowns_lyr", "CLEAR_SELECTION")
    arcpy.SelectLayerByAttribute_management("stems_lyr", "CLEAR_SELECTION")
    arcpy.management.SelectLayerByLocation(
        in_layer="stems_lyr",
        overlap_type="WITHIN",
        select_features="crowns_lyr",
        search_distance=None,
        selection_type="NEW_SELECTION",
        invert_spatial_relationship="INVERT",
    )

    # if selection > 1:
    if int(arcpy.GetCount_management("stems_lyr").getOutput(0)) > 1:
        logger.error("WARNING: Some stems do not fall within a crown polygon contain.")
        logger.info("Crowns are estimated using a buffer based on crown_radius.")
        logger.info(
            "Copy crowns manual into fc 'crowns_all' and 'crowns_in_situ using ArcGIS Pro."
        )
        # if crown_radius is empty set to buffer distance to 1m
        if municipality == "baerum":
            buffer_distance_attr_field = 1
        else:
            buffer_distance_attr_field = "crown_radius"

        arcpy.analysis.Buffer(
            in_features="stems_lyr",
            out_feature_class=fc_output,
            buffer_distance_or_field=buffer_distance_attr_field,
            line_side="FULL",
            line_end_type="ROUND",
            dissolve_option="NONE",
            dissolve_field=None,
            method="PLANAR",
        )

    arcpy.Delete_management("crowns_lyr")
    arcpy.Delete_management("stems_lyr")

    return False


if __name__ == "__main__":
    """Load data from raw to interim."""

    # set up logger
    setup_logging()
    logger = logging.getLogger(__name__)

    if quality_check():
        logger.info("Crowns are correctly matched to stems.")
        logger.info("END OF TASK: JOIN DATA")
        exit()
    else:
        logger.info("Crowns are not yet correctly matched to stems.")
        logger.info("START JOINING DATA...")

        # run script
        n_rounds = (1, 2)
        input(
            "Close any ArcGIS Pro Instances before running this code! \
            Press Enter to continue..."
        )

        # two rounds of point and polygon matching
        # round 1: per neighbourhood
        # round 2: whole study area (control: ensure borders of neighbourhoods)
        for counter in n_rounds:
            join_data(round=counter)

        # merge crowns in-situ and all crowns
        merge_data()
        # copy output to geo_relation.gdb
        copy_output()
        # check if crowns are correctly matched to stems
        quality_check()
        logger.info("END OF TASK: JOIN DATA")

# --------------------------------------------------------------------------- #
