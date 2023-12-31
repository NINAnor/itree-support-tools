"""
Code adapted from: https://github.com/zofie-cimburova/i-Tree-Eco/blob/main/distance_direction.py
COPYRIGHT:  (C) 2022 by Zofie Cimburova
"""

import os

import arcpy
from arcpy import env

# local sub-package utils
from src import arcpy_utils as au

# TODO load data_paths from catalog.yaml
# from src import INTERIM_PATH


def distance_to_building(filegdb, v_stem, v_crown_path, v_residential_buildings):
    env.workspace = filegdb_path
    l_buildings = arcpy.MakeFeatureLayer_management(
        v_residential_buildings, "tmp_building_layer"
    )

    field_list = [
        "bld_dist_1",
        "bld_dist_2",
        "bld_dist_3",
        "bld_dir_1",
        "bld_dir_2",
        "bld_dir_3",
    ]
    for field in field_list:
        au.addField_ifNotExists(v_stem, field, "DOUBLE")
        au.addField_ifNotExists(v_crown_path, field, "DOUBLE")

    expression = "boligbebyggelse = '1' And boligbygg_etg = '4 eller under'"
    arcpy.SelectLayerByAttribute_management(l_buildings, "NEW_SELECTION", expression)

    tmp_dissolve = os.path.join(filegdb, "tmp_dissolve_boligbygg")
    # arcpy.Dissolve_management(
    #     l_buildings,
    #     tmp_dissolve,
    #     dissolve_field="",
    #     statistics_fields="",
    #     multi_part="SINGLE_PART",
    #     unsplit_lines="DISSOLVE_LINES",
    # )

    # bodo
    arcpy.gapro.DissolveBoundaries(
        input_layer=l_buildings,
        out_feature_class=tmp_dissolve,
        multipart="SINGLE_PART",
        dissolve_fields=None,
        fields=None,
        summary_fields=None,
    )

    t_near = os.path.join(filegdb, "tmp_near_table")
    arcpy.GenerateNearTable_analysis(
        v_stem,
        v_residential_buildings,
        t_near,
        search_radius="18,3 Meters",
        location="NO_LOCATION",
        angle="ANGLE",
        closest="ALL",
        closest_count="3",
        method="PLANAR",
    )

    au.addField_ifNotExists(t_near, "NEAR_AZIMUTH", "Double")
    codeblock = """def toAzimuth(angle):
    azimuth = -1*angle+90
    if azimuth < 0:
        return 360+ azimuth
    else:
        return azimuth"""

    # use near angle to calculate near azimuth
    arcpy.CalculateField_management(
        t_near, "NEAR_AZIMUTH", "toAzimuth(!NEAR_ANGLE!)", "PYTHON_9.3", codeblock
    )

    ## split near table
    for i in [1, 2, 3]:
        arcpy.TableToTable_conversion(
            t_near,
            filegdb_path,
            "temp_near_table_{}".format(i),
            "NEAR_RANK = {}".format(i),
        )

    arcpy.Delete_management(t_near)
    au.join_and_copy(
        t_dest=v_stem_path,
        join_a_dest="OBJECTID",
        t_src=os.path.join(filegdb_path, "temp_near_table_1"),
        join_a_src="IN_FID",
        a_src=["NEAR_DIST", "NEAR_AZIMUTH"],
        a_dest=["bld_dist_1", "bld_dir_1"],
    )

    au.join_and_copy(
        t_dest=v_stem_path,
        join_a_dest="OBJECTID",
        t_src=os.path.join(filegdb_path, "temp_near_table_2"),
        join_a_src="IN_FID",
        a_src=["NEAR_DIST", "NEAR_AZIMUTH"],
        a_dest=["bld_dist_2", "bld_dir_2"],
    )

    au.join_and_copy(
        t_dest=v_stem_path,
        join_a_dest="OBJECTID",
        t_src=os.path.join(filegdb_path, "temp_near_table_3"),
        join_a_src="IN_FID",
        a_src=["NEAR_DIST", "NEAR_AZIMUTH"],
        a_dest=["bld_dist_3", "bld_dir_3"],
    )

    au.join_and_copy(
        t_dest=v_crown_path,
        join_a_dest="tree_id",
        t_src=v_stem_path,
        join_a_src="tree_id",
        a_src=field_list,
        a_dest=field_list,
    )

    arcpy.Delete_management([t_near, tmp_dissolve, l_buildings])


if __name__ == "__main__":
    pass

    # field calculator code block
    codeblock = """
        def is_null_building(building):
        if building is None:
            return -1
        else:
            return building
        """
