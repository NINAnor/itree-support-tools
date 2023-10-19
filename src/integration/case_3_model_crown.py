# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------- #
# Name: template.py
# Date: 2023-07-27
# Description:
# Author: Willeke A'Campo
# Dependencies:
# --------------------------------------------------------------------------- #

import logging
import os

import arcpy
from arcpy import env

from src.attributes.geo_relation_rule_attributes import RuleAttributes

# from src import ADMIN_GDB, INTERIM_PATH, MUNICIPALITY, SPATIAL_REFERENCE, RuleAttributes
from src.utils import arcpy_utils as au


def buffer_per_nb(
    neighbourhood_list: list, gdb_stems: str, spatial_reference: str, municipality
):
    from pathlib import Path

    interim_path = Path(gdb_stems).parent

    logger = logging.getLogger(__name__)
    logger.info(
        "Iterate over neighbourhoods and model crown geometry for CASE 3 stems)"
    )
    logger.info("Processing")

    # Detect trees per neighbourhood
    for n_code in neighbourhood_list:
        logger.info("-------------------------------------------------------------")
        logger.info("CASE 3: BUFFER TREE STEMS FOR NEIGHBOURHOOD <<{}>>".format(n_code))
        logger.info("-------------------------------------------------------------")

        # ------------------------------------------------------ #
        # Dynamic Path Variables
        # ------------------------------------------------------ #

        filegdb_path = os.path.join(
            interim_path, "geo_relation", "round_1_b" + n_code + ".gdb"
        )

        # input
        v_stems_c3 = os.path.join(filegdb_path, "stems_c3")
        v_crowns_raw = os.path.join(
            interim_path, "input_crowns.gdb", "b_" + n_code + "_kroner"
        )

        # temp
        v_buffer = os.path.join(filegdb_path, "tmp_c3_buffer")
        v_erase = os.path.join(filegdb_path, "tmp_c3_erase_ALScrown")
        v_dissolve = os.path.join(filegdb_path, "tmp_c3_dissolve")

        # output
        out_name = "crowns_c3_modelled"
        v_crowns_c3_modelled = os.path.join(filegdb_path, out_name)

        # workspace settings
        env.overwriteOutput = True
        env.outputCoordinateSystem = arcpy.SpatialReference(spatial_reference)
        # env.workspace = filegdb_path

        # compute buffer based on crown_radius
        if arcpy.Exists(v_crowns_c3_modelled):
            arcpy.Delete_management(v_crowns_c3_modelled)
            logger.info("v_crowns_c3_modelled already exists. Delete file")

        # init class
        rule_attribute = RuleAttributes(filegdb_path, v_stems_c3)
        rule_attribute.attr_ruleCrown()

        # model crown by creating a buffer with radius = crown_radius

        # if crown_radius is empty set to buffer distance to 1m
        if municipality == "baerum":
            buffer_distance_attr_field = 1
        else:
            buffer_distance_attr_field = "crown_radius"

        arcpy.Buffer_analysis(
            v_stems_c3, v_buffer, buffer_distance_attr_field, "", "", "ALL"
        )

        # subtract ALS crowns from buffer
        arcpy.Erase_analysis(v_buffer, v_crowns_raw, v_erase)

        # dissolve
        arcpy.Dissolve_management(v_erase, v_dissolve)

        # Convert to singlepart (Buffer tool creates one multipolygon object)
        arcpy.MultipartToSinglepart_management(v_dissolve, v_crowns_c3_modelled)

        # add fields to the new feature class
        au.addField_ifNotExists(v_crowns_c3_modelled, "geo_relation", "TEXT")
        arcpy.CalculateField_management(
            v_crowns_c3_modelled, "geo_relation", "'Case 3'", "PYTHON_9.3"
        )
        au.addField_ifNotExists(v_crowns_c3_modelled, "bydelnummer", "TEXT")
        arcpy.CalculateField_management(
            v_crowns_c3_modelled, "bydelnummer", str(n_code), "PYTHON_9.3"
        )

        # delete temporary files
        files = [v_buffer, v_erase, v_dissolve]
        for file in files:
            arcpy.Delete_management(file)


# check if can be deleted
def buffer_study_area(filegdb_path, v_crowns_all, spatial_reference, municipality):
    # ------------------------------------------------------ #
    # Dynamic Path Variables
    # ------------------------------------------------------ #
    logger = logging.getLogger(__name__)
    logger.info("-------------------------")
    logger.info("CASE 3: BUFFER TREE STEMS")
    logger.info("-------------------------")

    # input
    v_stems_c3 = os.path.join(filegdb_path, "stems_c3")

    # temp
    v_buffer = os.path.join(filegdb_path, "tmp_c3_buffer")
    v_erase = os.path.join(filegdb_path, "tmp_c3_erase_ALScrown")
    v_dissolve = os.path.join(filegdb_path, "tmp_c3_dissolve")
    v_singlepart = os.path.join(filegdb_path, "tmp_c3_singlepart")

    # output
    out_name = "crowns_c3_modelled"
    v_crowns_c3_modelled = os.path.join(filegdb_path, out_name)

    # workspace settings
    env.overwriteOutput = True
    env.outputCoordinateSystem = arcpy.SpatialReference(spatial_reference)
    env.workspace = filegdb_path

    # compute buffer based on crown_radius
    if arcpy.Exists(v_crowns_c3_modelled):
        arcpy.Delete_management(v_crowns_c3_modelled)
        logger.info("v_crowns_c3_modelled already exists. Delete file")

    # init class
    rule_attribute = RuleAttributes(filegdb_path, v_stems_c3)
    rule_attribute.attr_ruleCrown()

    # model crown by creating a buffer with radius = crown_radius
    if municipality == "baerum":
        buffer_distance_attr_field = 1
    else:
        buffer_distance_attr_field = "crown_radius"

    arcpy.Buffer_analysis(
        v_stems_c3, v_buffer, buffer_distance_attr_field, "", "", "ALL"
    )

    # subtract ALS crowns from buffer
    arcpy.Erase_analysis(v_buffer, v_crowns_all, v_erase)

    # dissolve
    arcpy.Dissolve_management(v_erase, v_dissolve)

    # Convert to singlepart (Buffer tool creates one multipolygon object)
    arcpy.MultipartToSinglepart_management(v_dissolve, v_crowns_c3_modelled)

    # add fields to the new feature class
    au.addField_ifNotExists(v_crowns_c3_modelled, "geo_relation", "TEXT")
    au.calculateField_ifEmpty(v_crowns_c3_modelled, "geo_relation", "'Case 3'")

    # delete temporary files
    files = [v_buffer, v_erase, v_dissolve, v_singlepart]
    for file in files:
        arcpy.Delete_management(file)


if __name__ == "__main__":
    pass
