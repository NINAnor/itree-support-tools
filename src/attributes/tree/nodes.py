import logging

import arcpy
from arcpy import env

from src.config.config import load_parameters
from src.utils import arcpy_utils as au

parameters = load_parameters()
municipality = parameters["municipality"]
spatial_reference = parameters["spatial_reference"][municipality]


def crown_structure(filegdb_path):
    logger = logging.getLogger(__name__)
    logger.info("CROWN ATTRIBUTES")

    # workspace settings
    env.overwriteOutput = True
    env.outputCoordinateSystem = arcpy.SpatialReference(spatial_reference)
    env.workspace = filegdb_path

    # 0. CROWN ID
    AdminAttribute.attr_crownID("nb_code")

    # 1. TREE HEIGHT (first!) (height_origin, height_total_tree)
    RuleAttribute.attr_ruleHeight()

    # 2. CROWN DIMENSIONS
    GeometryAttribute.attr_crownDiam()
    # (crown_origin, crown_diam, crown_radius)
    RuleAttribute.attr_ruleCrown()
    GeometryAttribute.attr_crownArea()  # crown_area and crown_perimeter
    GeometryAttribute.attr_crownVolume()

    # CROWN WIDTH NS and EW
    GeometryAttribute.attr_envelope(keep_temp=False)

    # 3. DBH (dbh_origin, dbh, dbh_height)
    InsituAttribute.attr_dbh()
    logger.info("Finished calculating attributes for the detected trees ...")

    # remove fields
    fields_to_delete = ["EV_length", "EV_width", "EV_area"]
    arcpy.DeleteField_management(v_crown, fields_to_delete)
    print("Fields removed: ", fields_to_delete)
    return


def crown_condition(filegdb_path, v_crown):
    au.addField_ifNotExists(v_crown, "crown_dieback", "SHORT")
    au.addField_ifNotExists(v_crown, "percent_missing_crown", "SHORT")
    return


def crown_to_stem(filegdb_path):
    logger = logging.getLogger(__name__)
    logger.info("JOIN CROWN AND STEM")

    # workspace settings
    env.overwriteOutput = True
    env.outputCoordinateSystem = arcpy.SpatialReference(spatial_reference)
    env.workspace = filegdb_path

    # CROWN ID
    AdminAttribute.join_crownID_toTop()
    return


f
