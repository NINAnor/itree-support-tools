import logging
import os


# local sub-package utils
# local sub-package modules
from src import (
    ADMIN_GDB,
    INTERIM_PATH,
    AdminAttributes,
    GeometryAttributes,
    InsituAttributes,
    RuleAttributes,
)
from src import arcpy_utils as au
from src import logger


def calculate_crown_condition(filegdb, v_crown):
    au.addField_ifNotExists(v_crown, "crown_dieback", "SHORT")
    au.addField_ifNotExists(v_crown, "percent_missing_crown", "SHORT")

    # CROWN LIGHT EXPOSURE

    codeblock = """def calculate_cle_class(cle_percent):
    if cle_percent <= -999:
        return 0
    if cle_percent <= 0.125:
        return 5
    elif cle_percent <= 0.375:
        return 4
    elif cle_percent <= 0.625:
        return 3
    elif cle_percent <= 0.875:
        return 2
    else:
        return 1
    """
    # calculate_cle_class(!cle_percent!)

    codeblock = """
    def calculate_cle_class(cle_percent):
    if cle_percent <= -999:
        return 0
    else:
        return cle_percent
    """

    codeblock = """
    def is_null_building(building):
    if building is None:
        return -1
    else:
        return building
        """


"""def calculate_total_tree(tree_height_laser, height_insitu,dbh):
    if tree_height_laser != None:
        return tree_height_laser
    elif height_insitu == "0-5":
        return 5
    elif height_insitu == "05-10":
        return 10
    elif height_insitu == "10-15":
        return 15
    elif height_insitu == "15-20":
        return 20
    elif height_insitu == "20-25":
        return 25
    elif dbh != None:
         return (dbh*1.22)/(4.04**1.22)
    else:
        return None"""

query = "tree_id LIKE 'itree\_0%' ESCAPE '' Or tree_id LIKE 'itree\_5%' ESCAPE '' Or tree_id LIKE 'itree\_6%' ESCAPE '' Or tree_id LIKE 'itree\_7%' ESCAPE '' Or tree_id LIKE 'itree\_8%' ESCAPE '' Or tree_id LIKE 'itree\_9%' ESCAPE ''"


if __name__ == "__main__":
    # setup logger
    logger.setup_logger(logfile=True)
    logger = logging.getLogger(__name__)

    filegdb_path = os.path.join(
        INTERIM_PATH, "itree_attributes", "itree_tree_attributes.gdb"
    )
    v_crown_path = os.path.join(filegdb_path, "itree_crowns")
    v_stem_path = os.path.join(filegdb_path, "itree_stems")
    v_crown = "itree_crowns"
    v_stem = "itree_stems"

    v_neighbourhoods = os.path.join(ADMIN_GDB, "bydeler")

    # P-DRIVE PATHS KRISTIANSAND
    v_residential_buildings = r"P:\152022_itree_eco_ifront_synliggjore_trars_rolle_i_okosyst\data\kristiansand\general\kristiansand_arealdata.gdb\fkb_boligbygg_omrade"  # # P-DRIVE PATHS BODO
    v_residential_buildings = r"P:\152022_itree_eco_ifront_synliggjore_trars_rolle_i_okosyst\data\bodo\general\bodo_arealdata.gdb\fkb_boligbygg_omrade"

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

    # Step 1 Overla analaysis
    # subroutine overlay_attributes.py

    # Step 2 Recalculate tree height, tree crown and tree dbh attributes
    # subroutine tree_attribtues.py
    tree_attributes(filegdb_path)
    join_crown_stem(filegdb_path)

    # Step 3 Calculate distance to building
    # TODO delete stems with no crown_id MANUALLY!
    distance_to_building(
        filegdb_path, v_stem_path, v_crown_path, v_residential_buildings
    )

    # Step 4 Calculate crown condition
    print("run CLE in separate script, from separate gdb, join crown attr to stmes!")
