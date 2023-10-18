import logging
import os

import arcpy
from arcpy import env

# TODO load data_paths from catalog.yaml
# local sub-package utils
# local sub-package modules
from src import (
    ADMIN_GDB,
    DATA_PATH,
    INTERIM_PATH,
    SPATIAL_REFERENCE,
    AdminAttributes,
    GeometryAttributes,
    InsituAttributes,
    RuleAttributes,
)
from src import arcpy_utils as au


def join_crown_stem(filegdb_path):
    logger = logging.getLogger(__name__)
    logger.info("JOIN CROWN AND STEM")

    # workspace settings
    env.overwriteOutput = True
    env.outputCoordinateSystem = arcpy.SpatialReference(SPATIAL_REFERENCE)
    env.workspace = filegdb_path

    # CROWN ID
    AdminAttribute.join_crownID_toTop()


def tree_attributes(filegdb_path):
    logger = logging.getLogger(__name__)
    logger.info("CROWN ATTRIBUTES")

    # workspace settings
    env.overwriteOutput = True
    env.outputCoordinateSystem = arcpy.SpatialReference(SPATIAL_REFERENCE)
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


def calculate_crown_condition(filegdb, v_crown):
    au.addField_ifNotExists(v_crown, "crown_dieback", "SHORT")
    au.addField_ifNotExists(v_crown, "percent_missing_crown", "SHORT")

    # CROWN LIGHT EXPOSURE


if __name__ == "__main__":
    filegdb_path = os.path.join(
        INTERIM_PATH, "itree_attributes", "itree_tree_attributes.gdb"
    )
    v_crown_path = os.path.join(filegdb_path, "itree_crowns")
    v_stem_path = os.path.join(filegdb_path, "itree_stems")
    v_crown = "itree_crowns"
    v_stem = "itree_stems"

    v_neighbourhoods = os.path.join(ADMIN_GDB, "bydeler")

    # init class to calculate attributes
    AdminAttribute = AdminAttributes(filegdb_path, v_crown, v_stem)
    InsituAttribute = InsituAttributes(filegdb_path, v_crown)
    GeometryAttribute = GeometryAttributes(filegdb_path, v_crown, v_stem)
    RuleAttribute = RuleAttributes(filegdb_path, v_crown)

    # TODO automate pre-processing
    # Add XY to stem points
    # Join stem to crown (one-to-one, contains, join_count = 1)
    input(
        "Check if crown layer contains tree stem attributes\
            and XY coord. Press Enter to continue..."
    )

    tree_attributes(filegdb_path)
    join_crown_stem(filegdb_path)

    # BODO SPECIFIC HEIGHT
    codeblock = """def calculate_total_tree(height_class):
    if height_class is None:
        return height_class  # Return None if the value is already null
    elif height_class == "0-5":
        return 5
    elif height_class == "5-10":
        return 10
    elif height_class == "10-25":
        return 15
    elif height_class == "15-20":
        return 20
    elif height_class == "20-25":
        return 25
    else:
        return height_class
        """

    arcpy.CalculateField_management(
        in_table=v_crown_path,
        field="height_total_tree",
        experssion="calculate_total_tree(!height_insitu!)",
        code_block=codeblock,
        expression_type="PYTHON_9.3",
    )
