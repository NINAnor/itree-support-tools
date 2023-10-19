import logging
import os

import arcpy
from arcpy import env

# local packages
# from src import ADMIN_GDB, INTERIM_PATH, MUNICIPALITY, SPATIAL_REFERENCE
from src.utils import arcpy_utils as au


def merge_per_nb(neighbourhood_list, gdb_stems, spatial_reference, round):
    logger = logging.getLogger(__name__)

    from pathlib import Path

    interim_path = Path(gdb_stems).parent

    # Detect trees per neighbourhood
    for n_code in neighbourhood_list:
        logger.info("-------------------------------------------------------------")
        logger.info("MERGE CASES PER NEIGHBOURHOOD <<{}>>".format(n_code))
        logger.info("-------------------------------------------------------------")
        logger.info(
            "Merge Case 1, split Case 2 and re-modelled Case 3 crowns per neighbourhood."
        )
        # input data
        # input
        filegdb_path = os.path.join(
            interim_path, "geo_relation", "round_" + str(round) + "_b" + n_code + ".gdb"
        )

        au.createGDB_ifNotExists(filegdb_path)
        # output
        output_gdb = os.path.join(
            interim_path, "geo_relation", "merge_round_" + str(round) + ".gdb"
        )
        au.createGDB_ifNotExists(output_gdb)
        # workspace settings
        env.overwriteOutput = True
        env.outputCoordinateSystem = arcpy.SpatialReference(spatial_reference)
        # not necessary as full paths are used, change accordingly if you work with relative paths
        env.workspace = filegdb_path

        # ------------------------------------------------------ #
        # Dynamic Path Variables
        # ------------------------------------------------------ #

        # output
        v_crowns_insitu = os.path.join(output_gdb, "crowns_insitu_b_" + n_code)
        v_crowns_c4 = os.path.join(output_gdb, "crowns_c4_b_" + n_code)

        # ------------------------------------------------------ #
        # 3. Merge detected trees into one file
        # ------------------------------------------------------ #
        logger.info("-" * 100)
        logger.info("1 Merging detected trees into one file...")
        logger.info("-" * 100)

        logger.info("Start merging...")

        # workspace MUST be set to gdb where c1, c2, c3, c4 are located
        env.workspace = filegdb_path
        c1 = "crowns_c1"
        c2 = "crowns_c2_split"
        c3 = "crowns_c3_modelled"
        c4 = "crowns_c4"
        fc_list = [c1, c2, c3]
        fc_list = [fc for fc in fc_list if au.exists_and_has_features(fc)]

        # clean fc_list
        for fc in fc_list:
            clean(fc)

        # merge based on number of files
        if len(fc_list) == 0:
            logger.info("No crowns detected. Continue ...")
            logger.info(fc_list)

        if len(fc_list) == 1:
            logger.info("Only one file detected. Copying to output ...")
            logger.info(fc_list)
            file_to_copy = fc_list[0]
            arcpy.CopyFeatures_management(file_to_copy, v_crowns_insitu)

        if len(fc_list) > 1:
            logger.info("More than one file detected. Merging to output ...")
            logger.info(fc_list)
            arcpy.Merge_management(
                inputs=fc_list, output=v_crowns_insitu, field_mappings="#"
            )

        # merge c4 files into one file
        arcpy.CopyFeatures_management(c4, v_crowns_c4)

    logger.info("Finished merging the crowns into one file ...")


def merge_study_area(input_gdb, ouput_fc):
    # merge all files within a list
    logger = logging.getLogger(__name__)
    logger.info("-------------------------------------------------------------")
    logger.info("MERGE NEIGHBOURHOOD CROWNS INTO ONE FILE")
    logger.info("-------------------------------------------------------------")

    au.createGDB_ifNotExists(input_gdb)
    env.workspace = input_gdb
    fc_list = arcpy.ListFeatureClasses()

    # drop if it exists
    # get base name from output_fc
    base_name = os.path.basename(ouput_fc)
    if base_name in fc_list:
        fc_list.remove(base_name)

    logger.info(f"Merge the features: {fc_list}")
    arcpy.Merge_management(inputs=fc_list, output=ouput_fc, field_mappings="#")


def merge_complete(input_gdb, fc_crowns_in_situ, fc_all_crowns):
    logger = logging.getLogger(__name__)
    logger.info("-------------------------------------------------------------")
    logger.info("MERGE FILES INTO <<ITREE_CROWNS>> AND <<ALL_CROWNS>>")
    logger.info("-------------------------------------------------------------")

    # workspace MUST be set to gdb where c1, c2, c3, c4 are located
    env.workspace = input_gdb
    c1 = "crowns_c1"
    c2 = "crowns_c2_split"
    c3 = "crowns_c3_modelled"
    c4 = "crowns_c4"
    fc_list = [c1, c2, c3]
    fc_list = [fc for fc in fc_list if au.exists_and_has_features(fc)]

    # if exists continue
    if not arcpy.Exists(fc_crowns_in_situ):
        logger.info(f"Merge the features: {fc_list}")
        arcpy.Merge_management(
            inputs=fc_list, output=fc_crowns_in_situ, field_mappings="#"
        )

    if not arcpy.Exists(fc_all_crowns):
        fc_all = fc_list
        fc_all.append(c4)
        logger.info(f"Merge the features: {fc_all}")
        arcpy.Merge_management(inputs=fc_all, output=fc_all_crowns, field_mappings="#")


def clean(input_fc):
    """Clean crowns after geo_relation

    Args:
    v_crowns (_type_): _description_
    """

    fields_to_keep = [
        "OBJECTID",
        "SHAPE",
        "bydelnummer",
        "Shape_Length",
        "Shape_Area",
        "n_code",
        "geo_relation",
        "seg_method",
        "tree_height_laser",
        "tree_altit",
        "nb_code",
        "stem_count",
        "stem_count2",
    ]
    fields = arcpy.ListFields(input_fc)

    fields_to_keep = [field.lower() for field in fields_to_keep]

    # delete all fields except the following
    fields_to_delete = []
    for field in fields:
        if field.name.lower() not in fields_to_keep:
            fields_to_delete.append(field.name)

    # if list is not empty list delete fields
    if fields_to_delete != []:
        arcpy.DeleteField_management(input_fc, fields_to_delete)

    return


if __name__ == "__main__":
    pass
