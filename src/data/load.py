"""Module to load raw data."""

# import  py-packages
import logging
import os

import arcpy

# import local packages
from src.utils import arcpy_utils as au


def copy_stems(raw_in_situ, gdb_input_stems):
    logger = logging.getLogger(__name__)

    # check if raw data exists
    if arcpy.Exists(raw_in_situ):
        logger.info(f"RAW in situ trees: \t\t{raw_in_situ}")
    else:
        logger.info(
            f"In-situ tree points do not exist. \n\
            Please check that the files are located in: {raw_in_situ}'"
        )
        exit()

    # check if interim data exists
    if arcpy.Exists(gdb_input_stems):
        logger.info(f"Existing INTERIM in situ trees: \t{gdb_input_stems}")
        return
    else:
        logger.info(f"Creating INTERIM in situ trees: \t{gdb_input_stems}")

        # create gdb
        au.createGDB_ifNotExists(gdb_input_stems)

        # path to in_situ_trees filegdb
        logger.info(f"INTERIM in situ trees: {gdb_input_stems}")

        arcpy.conversion.ExportFeatures(
            in_features=raw_in_situ,
            out_features=os.path.join(gdb_input_stems, "stems_in_situ"),
            where_clause="",
            use_field_alias_as_name="NOT_USE_ALIAS",
            field_mapping="#",
            sort_field=None,
        )

        # delete relationship class from table
        relation_table = os.path.join(gdb_input_stems, "stems_in_situ__ATTACH")
        if arcpy.Exists(relation_table):
            # delete relationship class from table
            arcpy.management.Delete(in_data=relation_table, data_type="")

    return


def copy_crowns(raw_laser, gdb_input_crowns):
    logger = logging.getLogger(__name__)

    # check if raw data exists
    if arcpy.Exists(raw_laser):
        logger.info(f"RAW laser tree crowns: \t{raw_laser}")
    else:
        logger.info(
            f"Laser crown polygons do not exist. \n\
            Please check that the files are located in: {raw_laser}"
        )
        exit()

    # check if interim data exists
    if arcpy.Exists(gdb_input_crowns):
        logger.info(f"Existing INTERIM laser tree crowns: \t{gdb_input_crowns}")
        return
    else:
        logger.info(f"Created INTERIM laser tree crowns: \t{gdb_input_crowns}")

        # create gdb
        au.createGDB_ifNotExists(gdb_input_crowns)

        # set env
        arcpy.env.workspace = raw_laser
        # loop over tree crown dataset and import all fc to gdb

        # List all feature classes in the geodatabase
        feature_classes = arcpy.ListFeatureClasses()
        # List all feature classes within feature datasets in the geodatabase
        for dataset in arcpy.ListDatasets("", "Feature"):
            for fc in arcpy.ListFeatureClasses("", "All", dataset):
                feature_classes.append(fc)

        for fc in feature_classes:
            # print fc name
            arcpy.conversion.ExportFeatures(
                in_features=fc,
                out_features=os.path.join(gdb_input_crowns, fc),
                where_clause="",
                use_field_alias_as_name="NOT_USE_ALIAS",
                field_mapping="#",
                sort_field=None,
            )

    return


def lookup_table(excel_path, sheet_name):
    import pandas as pd

    # import lookup table
    df = pd.read_excel(excel_path, sheet_name)

    return df
