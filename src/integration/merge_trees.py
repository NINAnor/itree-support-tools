import logging
import os

import arcpy
from arcpy import env

# local packages
from src import ADMIN_GDB, INTERIM_PATH, MUNICIPALITY, SPATIAL_REFERENCE
from src import arcpy_utils as au
from src import logger


def main(neighbourhood_list, round):

    logging.info(
        "Merge Case 1, split Case 2 and re-modelled Case 3 crowns into one file."
    )
    logging.info("-" * 100)
    logging.info("Processing neighbourhoods...")
    logging.info(neighbourhood_list)

    # Detect trees per neighbourhood
    for n_code in neighbourhood_list:
        logging.info("\t---------------------".format(n_code))
        logging.info("\tPROCESSING NEIGHBOURHOOD <<{}>>".format(n_code))
        logging.info("\t---------------------".format(n_code))

        # input data
        # output
        if round == 1:
            filegdb_path = os.path.join(
                INTERIM_PATH, "geo_relation", "round_1_b" + n_code + ".gdb"
            )

        if round == 2:
            filegdb_path = os.path.join(
                INTERIM_PATH, "geo_relation", "round_2_b" + n_code + ".gdb"
            )

        au.createGDB_ifNotExists(filegdb_path)

        output_gdb = os.path.join(
            INTERIM_PATH, "geo_relation", "merge_round_" + str(round) + ".gdb"
        )
        au.createGDB_ifNotExists(output_gdb)
        # workspace settings
        env.overwriteOutput = True
        env.outputCoordinateSystem = arcpy.SpatialReference(SPATIAL_REFERENCE)
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

        # ------------------------------------------------------ #
        # 3. Merge detected trees into one file
        # ------------------------------------------------------ #
        logging.info("-" * 100)
        logging.info("1 Merging detected trees into one file...")
        logging.info("-" * 100)

        logging.info("\tStart merging...")
        file_list = [v_crowns_c1, v_crowns_c2_split, v_crowns_c3_modelled]
        mergeable_files = [
            file
            for file in file_list
            if arcpy.Exists(file)
            and arcpy.GetCount_management(file).getOutput(0) != "0"
        ]

        if len(mergeable_files) == 0:
            logging.info("No crowns detected. Continue ...")
            print("No crowns detected. Continue ...")

        if len(mergeable_files) == 1:
            logging.info("Only one file detected. Copying to output ...")
            file_to_copy = mergeable_files[0]
            arcpy.CopyFeatures_management(file_to_copy, v_crowns_insitu)

        if len(mergeable_files) > 1:
            logging.info("More than one file detected. Merging to output ...")
            arcpy.Merge_management(inputs=mergeable_files, output=v_crowns_insitu)

    logging.info("Finished merging the crowns into one file ...")


def all(filegdb_path):

    # merge all files within a list

    logging.info("Merge the itree crowns per neighbourhood into one municipality file ")
    logging.info("-" * 100)

    env.workspace = filegdb_path
    fc_list = arcpy.ListFeatureClasses()

    print("input_file_list:", fc_list)
    logging.info("Merging neighbourhoods with in situ data ...")
    logging.info(fc_list)

    arcpy.Merge_management(
        inputs=fc_list, output=os.path.join(filegdb_path, "crowns_in_situ")
    )


if __name__ == "__main__":

    # setup logger
    logger.setup_logger(logfile=True)
    logger = logging.getLogger(__name__)

    # neighbourhood list
    neighbourhood_path = os.path.join(ADMIN_GDB, "bydeler")
    n_field_name = "bydelnummer"
    neighbourhood_list = au.get_neighbourhood_list(neighbourhood_path, n_field_name)

    main(neighbourhood_list, round=1)
    # all(neighbourhood_list)
