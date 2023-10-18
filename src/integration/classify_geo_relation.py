""" 
Classify the geometric relation between the stem points (in situ) and the crown polygons (laser)
Case 1: one polygon contains one point (1:1), simple join.  
Case 2: one polygon contains more than one point (1:n), split crown with voronoi tesselation.
Case 3: a point is not overlapped by any polygon (0:1), model tree crown using oslo formula.
Case 4: a polygon does not contain any point (1:0), not used to train i-tree eco/dataset for extrapolation.
"""

"""
output:

c4 crowns: non-itree crowns
c4 stems: 0 

c3 crowns: 0
c3 stems: x points 

v_crowns_c1_c2: itree crowns 
# join v_crowns_c1_c2 with v_stems_c1_c2
# count points in polygon 
# if larger than 1 -> c2 crowns
# else -> c1 crowns


v_stems_c1_c2: x points 

"""

import logging
import os

import arcpy
from arcpy import env

from src.compute_attributes.geo_relation_rule_attributes import RuleAttributes
from src.utils import arcpy_utils as au

# ------------------------------------------------------ #
# Functions
# ------------------------------------------------------ #


def export_c4_crowns(v_raw_crowns, v_raw_stems, v_crowns_c4):
    """Exports c4 crowns.
    (e.g. select crowns that do not intersect with any in situ stems)

    Args:
        v_raw_crowns (_type_): input polygons (raw laser tree crowns)
        v_raw_stems (_type_): input points (raw in situ stems)
        v_crowns_case4 (_type_): output polygons (case 4 crowns)
    """
    # laser crowns
    lyr_polygon = arcpy.MakeFeatureLayer_management(
        in_features=v_raw_crowns, out_layer="lyr_polygon"
    )
    # in situ stems
    lyr_point = arcpy.MakeFeatureLayer_management(
        in_features=v_raw_stems, out_layer="lyr_point"
    )

    # select points  that do not intersect with any in situ stems
    arcpy.SelectLayerByLocation_management(
        in_layer=lyr_polygon,
        overlap_type="INTERSECT",
        select_features=lyr_point,
        selection_type="NEW_SELECTION",
        invert_spatial_relationship="INVERT",
    )

    arcpy.CopyFeatures_management(lyr_polygon, v_crowns_c4)

    # add field
    au.addField_ifNotExists(
        featureclass=v_crowns_c4, fieldname="geo_relation", type="TEXT"
    )

    au.calculateField_ifEmpty(v_crowns_c4, "geo_relation", '"Case 4"')

    logging.info(f"Case 4 selected and exported to {os.path.basename(v_crowns_c4)}")

    # clear selection
    arcpy.SelectLayerByAttribute_management("lyr_polygon", "CLEAR_SELECTION")
    arcpy.SelectLayerByAttribute_management("lyr_point", "CLEAR_SELECTION")


def remove_c4_crowns(v_raw_crowns, v_raw_stems, v_crowns_c1_c2, filegdb_path):
    """
    Exports case 1 and case 2 rowns
    (e.g. remove case 4 crowns from the input crowns)

    Args:
        v_raw_crowns (_type_): input polygons (raw laser tree crowns)
        v_raw_stems (_type_): input points (raw in situ stems)
        v_crowns_c1_c2 (_type_): input points (case 1 and case 2 crowns)
    """

    # create a copy of v_raw_crowns otherwise you orginal data is altered
    temp_crowns = arcpy.CopyFeatures_management(
        v_raw_crowns, os.path.join(filegdb_path, "crowns_tmp")
    )

    # laser crowns
    lyr_polygon = arcpy.MakeFeatureLayer_management(
        in_features=temp_crowns, out_layer="lyr_polygon"
    )
    # in situ stems
    lyr_point = arcpy.MakeFeatureLayer_management(
        in_features=v_raw_stems, out_layer="lyr_point"
    )

    # select crowns that do not intersect with any in situ stems
    arcpy.SelectLayerByLocation_management(
        in_layer=lyr_polygon,
        overlap_type="INTERSECT",
        select_features=lyr_point,
        selection_type="NEW_SELECTION",
        invert_spatial_relationship="INVERT",
    )

    # Delete from the selection
    arcpy.DeleteFeatures_management(lyr_polygon)
    arcpy.CopyFeatures_management(lyr_polygon, v_crowns_c1_c2)

    # clear selection
    arcpy.SelectLayerByAttribute_management("lyr_polygon", "CLEAR_SELECTION")
    arcpy.SelectLayerByAttribute_management("lyr_point", "CLEAR_SELECTION")
    arcpy.Delete_management(temp_crowns)


def export_c3_stems(v_raw_crowns, v_raw_stems, v_stems_c3, filegdb_path):
    """Exports c3 stems.
    (e.g. select stems that do not intersect with any laser crowns)

    Args:
        v_raw_crowns (_type_): input polygons (raw laser tree crowns)
        v_raw_stems (_type_): input points (raw in situ stems)
        v_stems_c3 (_type_): output points (case 3 stems)
    """
    # laser crowns
    lyr_polygon = arcpy.MakeFeatureLayer_management(
        in_features=v_raw_crowns, out_layer="lyr_polygon"
    )
    # in situ stems
    lyr_point = arcpy.MakeFeatureLayer_management(
        in_features=v_raw_stems, out_layer="lyr_point"
    )

    # select stems that do not intersect with any laser crowns
    arcpy.SelectLayerByLocation_management(
        in_layer=lyr_point,
        overlap_type="INTERSECT",
        select_features=lyr_polygon,
        selection_type="NEW_SELECTION",
        invert_spatial_relationship="INVERT",
    )

    arcpy.CopyFeatures_management(lyr_point, v_stems_c3)

    # add field
    au.addField_ifNotExists(
        featureclass=v_stems_c3, fieldname="geo_relation", type="TEXT"
    )
    au.calculateField_ifEmpty(v_stems_c3, "geo_relation", '"Case 3"')

    logging.info(f"Case 3 selected and exported to {os.path.basename(v_stems_c3)}")

    # fill attribute values
    rule_attribue = RuleAttributes(filegdb_path, v_stems_c3)

    # clear selection
    arcpy.SelectLayerByAttribute_management("lyr_polygon", "CLEAR_SELECTION")
    arcpy.SelectLayerByAttribute_management("lyr_point", "CLEAR_SELECTION")


def remove_c3_stems(v_raw_crowns, v_raw_stems, v_stems_c1_c2, filegdb_path):
    """
    Exports case 1 and case 2 stems
    (e.g. remove case 3 stems from the input stems)

    Args:
        v_raw_crowns (_type_): input polygons (raw laser tree crowns)
        v_raw_stems (_type_): input stems (raw in situ stems)
        v_stems_c3 (_type_): output stems (case 1 and case 2 stems)
    """
    # create a copy of v_raw_stems otherwise you orginal data is altered
    temp_stems = arcpy.CopyFeatures_management(
        v_raw_stems, os.path.join(filegdb_path, "stems_tmp")
    )

    # laser crowns
    lyr_polygon = arcpy.MakeFeatureLayer_management(
        in_features=v_raw_crowns, out_layer="lyr_polygon"
    )
    # in situ stems
    lyr_point = arcpy.MakeFeatureLayer_management(
        in_features=temp_stems, out_layer="lyr_point"
    )

    # select stems that do not intersect with any laser crowns
    arcpy.SelectLayerByLocation_management(
        in_layer=lyr_point,
        overlap_type="INTERSECT",
        select_features=lyr_polygon,
        selection_type="NEW_SELECTION",
        invert_spatial_relationship="INVERT",
    )

    # Delete from the selection
    arcpy.DeleteFeatures_management(lyr_point)

    # export stems
    arcpy.CopyFeatures_management(lyr_point, v_stems_c1_c2)

    # clear selection
    arcpy.SelectLayerByAttribute_management("lyr_polygon", "CLEAR_SELECTION")
    arcpy.SelectLayerByAttribute_management("lyr_point", "CLEAR_SELECTION")
    arcpy.Delete_management(temp_stems)


def count_points_in_polygon(v_crowns_c1_c2, v_stems_c1_c2, v_crowns_c1_c2_joincount):
    """
    Counts the number of points in a polygon.

    Args:
        v_crowns_c1_c2 (str): input polygons (case 1 and case 2 crowns)
        v_stems_c1_c2 (str): input points (case 1 and case 2 stems)
        v_crowns_c1_c2_joincount (str): output polygons (case 1 and case 2 crowns with join count)
    """

    # ensure join coutn is deleted
    arcpy.DeleteField_management(v_stems_c1_c2, ["Join_Count", "TARGET_FID"])
    arcpy.DeleteField_management(v_crowns_c1_c2, ["Join_Count", "TARGET_FID"])

    arcpy.analysis.SpatialJoin(
        target_features=v_crowns_c1_c2,
        join_features=v_stems_c1_c2,
        out_feature_class=v_crowns_c1_c2_joincount,
        join_operation="JOIN_ONE_TO_ONE",
        match_option="CONTAINS",
    )


def export_c1_crowns(v_crowns_c1_c2_joincount, v_crowns_c1, round):
    """Exports case 1 crowns.
    (e.g. select crowns with join count = 1)

    Args:
        v_crowns_c1_c2_joincount (_type_): input polygons (case 1 and case 2 crowns with join count)
        c1_crowns (_type_): output polygons (case 1 crowns)
    """
    # classify geo relation based on Join_Count
    # if 1 -> case 1, if > 1 -> case 2
    query_c1 = "Join_Count = 1"  # (polygon:point = 1:1)

    # select case 1 crowns

    lyr_polgyon = arcpy.MakeFeatureLayer_management(
        in_features=v_crowns_c1_c2_joincount, out_layer="lyr_polygon"
    )

    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=lyr_polgyon,
        selection_type="NEW_SELECTION",
        where_clause=query_c1,
        invert_where_clause=None,
    )

    arcpy.CopyFeatures_management(lyr_polgyon, v_crowns_c1)
    au.addField_ifNotExists(v_crowns_c1, "geo_relation", "TEXT")
    au.calculateField_ifEmpty(v_crowns_c1, "geo_relation", '"Case 1"')

    logging.info(f"Case 1 selected and exported to {os.path.basename(v_crowns_c1)}")

    arcpy.AlterField_management(
        v_crowns_c1, "Join_Count", f"stem_count{round}", f"stem_count{round}"
    )
    arcpy.DeleteField_management(v_crowns_c1, ["Join_Count", "TARGET_FID"])

    # clear selection
    arcpy.SelectLayerByAttribute_management("lyr_polygon", "CLEAR_SELECTION")


def export_c2_crowns(v_crowns_c1_c2_joincount, v_crowns_c2, round):
    """Exports case 2 crowns.
    (e.g. select crowns with join count > 1)

    Args:
        v_crowns_c1_c2_joincount (_type_): input polygons (case 1 and case 2 crowns with join count)
        v_crowns_c2 (_type_): output polygons (case 2 crowns)
    """

    query_c2 = "Join_Count > 1"  # (polygon:point = 1:n)

    lyr_polgyon = arcpy.MakeFeatureLayer_management(
        in_features=v_crowns_c1_c2_joincount, out_layer="lyr_polygon"
    )

    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=lyr_polgyon,
        selection_type="NEW_SELECTION",
        where_clause=query_c2,
        invert_where_clause=None,
    )

    arcpy.CopyFeatures_management(lyr_polgyon, v_crowns_c2)
    au.addField_ifNotExists(v_crowns_c2, "geo_relation", "TEXT")
    au.calculateField_ifEmpty(v_crowns_c2, "geo_relation", '"Case 2"')

    logging.info(f"Case 2 selected and exported to {os.path.basename(v_crowns_c2)}")
    arcpy.AlterField_management(
        v_crowns_c2, "Join_Count", f"stem_count{round}", f"stem_count{round}"
    )
    arcpy.DeleteField_management(v_crowns_c2, ["Join_Count", "TARGET_FID"])
    # clear selection
    arcpy.SelectLayerByAttribute_management("lyr_polygon", "CLEAR_SELECTION")


def main(neighbourhood_list, gdb_crowns, gdb_stems, spatial_reference, round):
    from pathlib import Path

    interim_path = Path(gdb_crowns).parent

    logging.info(
        "Iterate over neighbourhoods and classify the geometric relation between the stem points (in situ) and the crown polygons (laser)"
    )
    logging.info("Processing")

    # Detect trees per neighbourhood
    for n_code in neighbourhood_list:
        logging.info("\t---------------------".format(n_code))
        logging.info("\tPROCESSING NEIGHBOURHOOD <<{}>>".format(n_code))
        logging.info("\t---------------------".format(n_code))

        # ------------------------------------------------------ #
        # Dynamic Path Variables
        # ------------------------------------------------------ #
        # input
        v_raw_stems = os.path.join(gdb_stems, f"b_{n_code}_stems")

        # output
        if round == 1:
            filegdb_path = os.path.join(
                interim_path, "geo_relation", "round_1_b" + n_code + ".gdb"
            )
            v_raw_crowns = os.path.join(gdb_crowns, f"b_{n_code}_kroner")

        if round == 2:
            filegdb_path = os.path.join(
                interim_path, "geo_relation", "round_2_b" + n_code + ".gdb"
            )
            v_raw_crowns = os.path.join(gdb_crowns, f"crowns_insitu_b_{n_code}")

        if round == 3:
            filegdb_path = os.path.join(
                interim_path, "geo_relation", "round_3_b" + n_code + ".gdb"
            )

        au.createGDB_ifNotExists(filegdb_path)

        v_crowns_c4 = os.path.join(filegdb_path, f"crowns_c4")
        v_crowns_c1_c2 = os.path.join(filegdb_path, f"crowns_c1_c2")
        v_stems_c3 = os.path.join(filegdb_path, f"stems_c3")
        v_stems_c1_c2 = os.path.join(filegdb_path, f"stems_c1_c2")

        v_crowns_c1_c2_joincount = os.path.join(filegdb_path, f"crowns_c1_c2_joincount")

        v_crowns_c1 = os.path.join(filegdb_path, f"crowns_c1")
        v_crowns_c2 = os.path.join(filegdb_path, f"crowns_c2")

        all_files = [
            v_crowns_c1,
            v_crowns_c2,
            v_crowns_c4,
            v_crowns_c1_c2,
            v_crowns_c1_c2_joincount,
            v_stems_c1_c2,
            v_stems_c3,
        ]
        for file in all_files:
            arcpy.Delete_management(file)

        # workspace settings
        env.overwriteOutput = True
        env.outputCoordinateSystem = arcpy.SpatialReference(spatial_reference)
        env.workspace = filegdb_path

        logging.info(
            "Start exporting CASE 4 crowns (e.g select crowns that do not intersect with any in situ stems)"
        )
        export_c4_crowns(v_raw_crowns, v_raw_stems, v_crowns_c4)

        logging.info(
            "Start exporting CASE 1 and CASE 2 crowns (e.g remove case 4 crowns from the input crowns)"
        )
        remove_c4_crowns(v_raw_crowns, v_raw_stems, v_crowns_c1_c2, filegdb_path)

        logging.info(
            "Start exporting CASE 3 stems (e.g select stems that do not intersect with any laser crowns)"
        )
        export_c3_stems(v_raw_crowns, v_raw_stems, v_stems_c3, filegdb_path)

        logging.info(
            "Start exporting CASE 1 and CASE 2 stems (e.g remove case 3 stems from the input stems)"
        )
        remove_c3_stems(v_raw_crowns, v_raw_stems, v_stems_c1_c2, filegdb_path)

        logging.info("Start counting points in polygon")
        # TODO ensure that no previous joing count exists!!
        count_points_in_polygon(v_crowns_c1_c2, v_stems_c1_c2, v_crowns_c1_c2_joincount)

        logging.info(
            "Start exporting CASE 1 crowns (e.g select crowns with join count = 1)"
        )
        export_c1_crowns(v_crowns_c1_c2_joincount, v_crowns_c1, round)

        logging.info(
            "Start exporting CASE 2 crowns (e.g select crowns with join count > 1)"
        )
        export_c2_crowns(v_crowns_c1_c2_joincount, v_crowns_c2, round)

        logging.info("Delete temporary files:")
        # delete temporary files
        arcpy.Delete_management(v_crowns_c1_c2)
        arcpy.Delete_management(v_stems_c1_c2)
        arcpy.Delete_management(v_crowns_c1_c2_joincount)


def all(v_crowns, v_stems, filegdb_path, spatial_reference, round):
    au.createGDB_ifNotExists(filegdb_path)

    v_crowns_c4 = os.path.join(filegdb_path, f"crowns_c4")
    v_crowns_c1_c2 = os.path.join(filegdb_path, f"crowns_c1_c2")
    v_stems_c3 = os.path.join(filegdb_path, f"stems_c3")
    v_stems_c1_c2 = os.path.join(filegdb_path, f"stems_c1_c2")

    v_crowns_c1_c2_joincount = os.path.join(filegdb_path, f"crowns_c1_c2_joincount")

    v_crowns_c1 = os.path.join(filegdb_path, f"crowns_c1")
    v_crowns_c2 = os.path.join(filegdb_path, f"crowns_c2")

    all_files = [
        v_crowns_c1,
        v_crowns_c2,
        v_crowns_c4,
        v_crowns_c1_c2,
        v_crowns_c1_c2_joincount,
        v_stems_c1_c2,
        v_stems_c3,
    ]
    for file in all_files:
        arcpy.Delete_management(file)

    # workspace settings
    env.overwriteOutput = True
    env.outputCoordinateSystem = arcpy.SpatialReference(spatial_reference)
    env.workspace = filegdb_path

    logging.info(
        "Start exporting CASE 4 crowns (e.g select crowns that do not intersect with any in situ stems)"
    )
    export_c4_crowns(v_crowns, v_stems, v_crowns_c4)

    logging.info(
        "Start exporting CASE 1 and CASE 2 crowns (e.g remove case 4 crowns from the input crowns)"
    )
    remove_c4_crowns(v_crowns, v_stems, v_crowns_c1_c2, filegdb_path)

    logging.info(
        "Start exporting CASE 3 stems (e.g select stems that do not intersect with any laser crowns)"
    )
    export_c3_stems(v_crowns, v_stems, v_stems_c3, filegdb_path)

    logging.info(
        "Start exporting CASE 1 and CASE 2 stems (e.g remove case 3 stems from the input stems)"
    )
    remove_c3_stems(v_crowns, v_stems, v_stems_c1_c2, filegdb_path)

    logging.info("Start counting points in polygon")
    # TODO ensure that no previous joing count exists!!
    count_points_in_polygon(v_crowns_c1_c2, v_stems_c1_c2, v_crowns_c1_c2_joincount)

    logging.info(
        "Start exporting CASE 1 crowns (e.g select crowns with join count = 1)"
    )
    export_c1_crowns(v_crowns_c1_c2_joincount, v_crowns_c1, round)

    logging.info(
        "Start exporting CASE 2 crowns (e.g select crowns with join count > 1)"
    )
    export_c2_crowns(v_crowns_c1_c2_joincount, v_crowns_c2, round)

    logging.info("Delete temporary files:")
    # delete temporary files
    arcpy.Delete_management(v_crowns_c1_c2)
    arcpy.Delete_management(v_stems_c1_c2)
    arcpy.Delete_management(v_crowns_c1_c2_joincount)


if __name__ == "__main__":
    pass
