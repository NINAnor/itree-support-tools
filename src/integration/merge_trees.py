import logging
import os

import arcpy
from arcpy import env

# local packages
# from src import ADMIN_GDB, INTERIM_PATH, MUNICIPALITY, SPATIAL_REFERENCE
from src.utils import arcpy_utils as au


def part_1(neighbourhood_list, gdb_stems, spatial_reference, round):
    logger = logging.getLogger(__name__)
    logger.info(
        "Merge Case 1, split Case 2 and re-modelled Case 3 crowns into one file."
    )
    logger.info("-" * 100)
    logger.info("Processing neighbourhoods...")
    logger.info(neighbourhood_list)

    from pathlib import Path

    interim_path = Path(gdb_stems).parent

    # Detect trees per neighbourhood
    for n_code in neighbourhood_list:
        logger.info("\t---------------------".format(n_code))
        logger.info("\tPROCESSING NEIGHBOURHOOD <<{}>>".format(n_code))
        logger.info("\t---------------------".format(n_code))

        # input data
        # output
        if round == 1:
            filegdb_path = os.path.join(
                interim_path, "geo_relation", "round_1_b" + n_code + ".gdb"
            )

        if round == 2:
            filegdb_path = os.path.join(
                interim_path, "geo_relation", "round_2_b" + n_code + ".gdb"
            )

        au.createGDB_ifNotExists(filegdb_path)

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

        # not modified
        v_crowns_c1 = os.path.join(filegdb_path, "crowns_c1")
        v_crowns_c2_split = os.path.join(filegdb_path, "crowns_c2_split")
        v_crowns_c3_modelled = os.path.join(filegdb_path, "crowns_c3_modelled")

        # output
        v_crowns_insitu = os.path.join(output_gdb, "crowns_insitu_b_" + n_code)
        v_crowns_c4 = os.path.join(output_gdb, "crowns_c4_b_" + n_code)
        # ------------------------------------------------------ #
        # 3. Merge detected trees into one file
        # ------------------------------------------------------ #
        logger.info("-" * 100)
        logger.info("1 Merging detected trees into one file...")
        logger.info("-" * 100)

        logger.info("\tStart merging...")
        file_list = [v_crowns_c1, v_crowns_c2_split, v_crowns_c3_modelled]
        mergeable_files = [
            file
            for file in file_list
            if arcpy.Exists(file)
            and arcpy.GetCount_management(file).getOutput(0) != "0"
        ]

        if len(mergeable_files) == 0:
            logger.info("No crowns detected. Continue ...")
            print("No crowns detected. Continue ...")

        if len(mergeable_files) == 1:
            logger.info("Only one file detected. Copying to output ...")
            file_to_copy = mergeable_files[0]
            arcpy.CopyFeatures_management(file_to_copy, v_crowns_insitu)

        if len(mergeable_files) > 1:
            logger.info("More than one file detected. Merging to output ...")
            arcpy.Merge_management(inputs=mergeable_files, output=v_crowns_insitu)

        # merge c4 files into one file
        arcpy.CopyFeatures_management("crowns_c4", v_crowns_c4)

    logger.info("Finished merging the crowns into one file ...")


def part_2(input_gdb):
    # merge all files within a list
    logger = logging.getLogger(__name__)
    logger.info("Merge the itree crowns per neighbourhood into one municipality file ")
    logger.info("-" * 100)

    au.createGDB_ifNotExists(input_gdb)
    env.workspace = input_gdb
    fc_list = arcpy.ListFeatureClasses()

    # drop crowns_in_situ if it exists
    if "crowns_in_situ" in fc_list:
        fc_list.remove("crowns_in_situ")

    print("input_file_list:", fc_list)
    logger.info("Merging neighbourhoods with in situ data ...")
    logger.info(fc_list)

    arcpy.Merge_management(
        inputs=fc_list, output=os.path.join(input_gdb, "crowns_in_situ")
    )


def part_3(input_gdb, fc_crowns_round_2, fc_all_crowns):
    logger = logging.getLogger(__name__)
    env.workspace = input_gdb
    c1 = "crowns_c1"
    c2 = "crowns_c2_split"
    c3 = "crowns_c3_modelled"
    c4 = "crowns_c4"
    fc_list = [c1, c2, c3]

    # remove fc from list if it does not exist
    fc_list = [fc for fc in fc_list if arcpy.Exists(fc)]

    for fc in fc_list:
        count = arcpy.GetCount_management(fc).getOutput(0)
        print("Count for feature class {}: {}".format(fc, count))
        if count == 0:
            # drop fc from list
            fc_list.remove(fc)
        else:
            continue

    # if exists continue
    if not arcpy.Exists(fc_crowns_round_2):
        logger.info(f"Merge the features: {fc_list}")
        arcpy.Merge_management(inputs=fc_list, output=fc_crowns_round_2)

    if not arcpy.Exists(fc_all_crowns):
        fc_all = fc_list
        fc_all.append(c4)
        logger.info(f"Merge the features: {fc_all}")
        arcpy.Merge_management(inputs=fc_all, output=fc_all_crowns)


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
        "bydelnummer",
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

    arcpy.DeleteField_management(input_fc, fields_to_delete)

    print("Fields removed: ", fields_to_delete)

    return


if __name__ == "__main__":
    pass
