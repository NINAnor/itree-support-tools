import logging
import os

import arcpy

# local sub-package utils
# local sub-package modules
from attributes import spatial_join
from src.utils import arcpy_utils as au

# TODO load data_paths from catalog.yaml
# from src import INTERIM_PATH, ADMIN_GDB


# insitu crowns/stems
def neighbourhood_stem(v_stem_path, v_crown_path, filegdb_path, v_neighbourhoods):
    au.createGDB_ifNotExists(filegdb_path)
    logger = logging.getLogger(__name__)
    fc_output = os.path.join(filegdb_path, "nb_tree_stem")
    if arcpy.Exists(fc_output):
        logger.info("Neighbourhood layer already exists. Skipping...")
        return

    au.addField_ifNotExists(v_crown_path, "nb_code", "TEXT")
    au.addField_ifNotExists(v_crown_path, "nb_name", "TEXT")

    join_field = "bydelnummer"
    target_field = "nb_code"
    spatial_join(
        v_stem_path,
        v_neighbourhoods,
        fc_output,
        join_field,
        target_field,
        match_option="HAVE_THEIR_CENTER_IN",
    )

    fields_to_keep = [
        "GlobalID",
        "OBJECTID",
        "Shape",
        "tree_id",
        "nb_code",
        "bydelnavn",
    ]

    for field in arcpy.ListFields(fc_output):
        if field.name not in fields_to_keep:
            arcpy.DeleteField_management(fc_output, field.name)

    # join to crown
    au.join_and_copy(
        t_dest=v_crown_path,
        join_a_dest="tree_id",
        t_src=fc_output,
        join_a_src="tree_id",
        a_src=["nb_code", "bydelnavn"],
        a_dest=["nb_code", "nb_name"],
    )


# all crowns
def neighbourhood_crown(v_crown_path, filegdb_path, v_neighbourhoods):
    au.createGDB_ifNotExists(filegdb_path)
    logger = logging.getLogger(__name__)
    fc_output = os.path.join(filegdb_path, "nb_tree_crown")

    au.addField_ifNotExists(v_crown_path, "nb_code", "TEXT")
    au.addField_ifNotExists(v_crown_path, "nb_name", "TEXT")

    join_field = "bydelnummer"
    target_field = "nb_code"
    spatial_join(
        v_crown_path,
        v_neighbourhoods,
        fc_output,
        join_field,
        target_field,
        match_option="LARGEST_OVERLAP",
    )

    fields_to_keep = [
        "OBJECTID",
        "Shape",
        "tree_height_laser",
        "tree_altit",
        "geo_relation",
        "nb_code",
    ]

    for field in arcpy.ListFields(fc_output):
        if field.name not in fields_to_keep:
            arcpy.DeleteField_management(fc_output, field.name)


def street_tree(v_stem_path, v_crown_path, filegdb_path, v_area_data):
    logger = logging.getLogger(__name__)
    v_street = os.path.join(v_area_data, "n50_vegsenterlinje_buffer10m")
    fc_output = os.path.join(filegdb_path, "itree_street_tree")
    if arcpy.Exists(fc_output):
        logger.info("Street tree already exists. Skipping...")
        return
    # "Y", "N"
    au.addField_ifNotExists(v_crown_path, "street_tree", "TEXT")

    join_field = "vegkategori"
    target_field = "street_tree"
    spatial_join(
        v_stem_path,
        v_street,
        fc_output,
        join_field,
        target_field,
        match_option="HAVE_THEIR_CENTER_IN",
    )

    with arcpy.da.UpdateCursor(fc_output, ["Join_Count", "street_tree"]) as cursor:
        for row in cursor:
            if row[0] == 0 or row[0] == None:
                row[1] = "N"
            else:
                row[1] = "Y"
            cursor.updateRow(row)

    fields_to_keep = ["GlobalID", "OBJECTID", "Shape", "tree_id", "street_tree"]

    for field in arcpy.ListFields(fc_output):
        if field.name not in fields_to_keep:
            arcpy.DeleteField_management(fc_output, field.name)
    # join to crown
    au.join_and_copy(
        t_dest=v_crown_path,
        join_a_dest="tree_id",
        t_src=fc_output,
        join_a_src="tree_id",
        a_src=["street_tree"],
        a_dest=["street_tree"],
    )


def privat_public(v_stem_path, v_crown_path, filegdb_path, v_property_data):
    logger = logging.getLogger(__name__)
    v_private_public = os.path.join(v_property_data, "privat_offentlig_omr")
    fc_output = os.path.join(filegdb_path, "itree_privat_public")
    if arcpy.Exists(fc_output):
        logger.info("Private_public layer already exists. Skipping...")
        return

    au.addField_ifNotExists(v_crown_path, "private_public", "TEXT")

    join_field = "privat_offentlig_omrade"
    target_field = "private_public"
    spatial_join(
        v_stem_path,
        v_private_public,
        fc_output,
        join_field,
        target_field,
        match_option="HAVE_THEIR_CENTER_IN",
    )

    with arcpy.da.UpdateCursor(fc_output, ["private_public"]) as cursor:
        for row in cursor:
            if row[0] == "privat":
                row[0] = "privat område"
            else:
                row[0] = "offentlig område"
            cursor.updateRow(row)

    fields_to_keep = ["GlobalID", "OBJECTID", "Shape", "tree_id", "private_public"]

    for field in arcpy.ListFields(fc_output):
        if field.name not in fields_to_keep:
            arcpy.DeleteField_management(fc_output, field.name)

    # join to crown
    au.join_and_copy(
        t_dest=v_crown_path,
        join_a_dest="tree_id",
        t_src=fc_output,
        join_a_src="tree_id",
        a_src=["private_public"],
        a_dest=["private_public"],
    )


def land_use(v_stem_path, v_crown_path, filegdb_path, v_area_data):
    logger = logging.getLogger(__name__)
    v_land_use = os.path.join(v_area_data, "itree_arealbruk")
    fc_output = os.path.join(filegdb_path, "itree_land_use")
    if arcpy.Exists(fc_output):
        logger.info("Land use layer already exists. Skipping...")
        return

    new_fields = [
        "itree_LU_kode",
        "itree_LU",
        "itree_ground_cover",
        "SSB_hoved_underklasse",
        "AR5_arealtype",
        "arealtype_navn",
    ]
    for field in new_fields:
        au.addField_ifNotExists(v_crown_path, field, "TEXT")

    join_field = "itree_LU_kode"
    target_field = "itree_LU_kode"

    spatial_join(
        v_stem_path,
        v_land_use,
        fc_output,
        join_field,
        target_field,
        match_option="HAVE_THEIR_CENTER_IN",
    )

    fields_to_keep = ["GlobalID", "OBJECTID", "Shape", "tree_id"]
    # append new fields to list
    fields_to_keep.extend(new_fields)
    print(fields_to_keep)

    for field in arcpy.ListFields(fc_output):
        if field.name not in fields_to_keep:
            arcpy.DeleteField_management(fc_output, field.name)

    # join to crown
    au.join_and_copy(
        t_dest=v_crown_path,
        join_a_dest="tree_id",
        t_src=fc_output,
        join_a_src="tree_id",
        a_src=new_fields,
        a_dest=new_fields,
    )


if __name__ == "__main__":
    pass
