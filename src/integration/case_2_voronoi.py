""" 
Model Crown Geometry for Case 2. 
Case 2: one polygon contains more than one point (1:n), split crown with voronoi tesselation.
"""
import logging
import os

import arcpy
from arcpy import env

# local packages
# from src import ADMIN_GDB, INTERIM_PATH, MUNICIPALITY, SPATIAL_REFERENCE
from src.utils import arcpy_utils as au


def voronoi(polygon_layer, point_layer, filegdb_path, v_crowns_c2_split, area_extent):
    """_summary_

    Parameters
    ----------
    polygon_layer : _type_
        _description_
    point_layer : _type_
        _description_
    filegdb_path : _type_
        _description_
    v_crowns_c2_split : _type_
        _description_
    """
    logger = logging.getLogger(__name__)
    count_crowns = int(arcpy.GetCount_management(polygon_layer).getOutput(0))
    logger.info(f"Count of Case 2 Crowns: {count_crowns}")

    # Split each tree crown based on the number of stems.
    fields = ["OBJECTID", "crown_id"]
    with arcpy.da.SearchCursor(polygon_layer, fields) as cursor:
        for row in cursor:
            logger.info(
                f"START SPLITTING TREECROWN, OBJECTID: {row[0]}, crown_id: {row[1]}"
            )
            # reset environment extent!
            env.extent = polygon_layer
            # select tree crown by crown_id
            polygon_id = str(row[1])

            # temporary layers that have to be deleted and cleared!
            tmp_crown_lyr = os.path.join(filegdb_path, "temp_crown_" + polygon_id)
            tmp_thiessen_lyr = os.path.join(filegdb_path, "temp_thiessen_" + polygon_id)
            tmp_split_crown_lyr = os.path.join(
                filegdb_path, "temp_split_crown_" + polygon_id
            )
            tmp_selected_points = os.path.join(
                filegdb_path, "temp_selected_points_" + polygon_id
            )

            # create a layer for the selected polygon
            arcpy.MakeFeatureLayer_management(
                polygon_layer, "selected_polygon", f"CROWN_ID = '{polygon_id}'"
            )
            arcpy.CopyFeatures_management(
                "selected_polygon", tmp_crown_lyr
            )  # tree crown

            # Create point layer
            arcpy.MakeFeatureLayer_management(point_layer, "point_lyr")
            arcpy.SelectLayerByLocation_management(
                in_layer="point_lyr",  # selected points
                overlap_type="INTERSECT",
                select_features=tmp_crown_lyr,  # crown
                selection_type="NEW_SELECTION",
            )

            # selected points
            arcpy.CopyFeatures_management(
                "point_lyr", tmp_selected_points
            )  # tree crown

            # log the tree_id values of the selected stem points
            fields_pnt = ["OBJECTID", "tree_id"]
            with arcpy.da.SearchCursor(tmp_selected_points, fields_pnt) as cursor:
                for row in cursor:
                    logger.info(f"selected_point: {row[0]}, tree_id: {row[1]}")

                # split the treecrown using the thiessen polygons
            env.extent = tmp_crown_lyr  # tree crown area
            env.overwriteOutput = True

            arcpy.CreateThiessenPolygons_analysis(tmp_selected_points, tmp_thiessen_lyr)
            arcpy.Intersect_analysis(
                [tmp_thiessen_lyr, tmp_crown_lyr], tmp_split_crown_lyr
            )

            # Create featureclass if not exists
            if not arcpy.Exists(v_crowns_c2_split):
                arcpy.CreateFeatureclass_management(
                    filegdb_path,
                    "crowns_c2_split",
                    geometry_type="POLYGON",
                    spatial_reference=tmp_split_crown_lyr,
                )
                # add fields to the new feature class
                field_list = [
                    "geo_relation",
                    "stem_count",
                    "seg_method",
                    "bydelnummer",
                    "crown_id",
                    "tree_height_laser",
                    "tree_altit",
                ]
                field_type = [
                    "TEXT",
                    "LONG",
                    "TEXT",
                    "TEXT",
                    "TEXT",
                    "FLOAT",
                    "FLOAT",
                ]

                for field, field_type in zip(field_list, field_type):
                    au.addField_ifNotExists(v_crowns_c2_split, field, field_type)

                logger.info(
                    "Target feature class '{}' created.".format(v_crowns_c2_split)
                )

            # append the splitted crowns to crowns_c2_split
            arcpy.Append_management(
                inputs=tmp_split_crown_lyr,
                target=v_crowns_c2_split,
                schema_type="NO_TEST",
                field_mapping=None,
                subtype="",
                expression="",
                match_fields=None,
                update_geometry="NOT_UPDATE_GEOMETRY",
            )

            count_appended_crowns = int(
                arcpy.GetCount_management(tmp_split_crown_lyr).getOutput(0)
            )
            logger.info(f"Appended crowns: {count_appended_crowns}")

            # uncomment for complet logging
            # fields_polygon= ["OBJECTID", "crown_id"]
            # with arcpy.da.SearchCursor(v_crowns_c2_split, fields_polygon) as cursor:
            #     for row in cursor:
            #         logger.info(
            #             f"Appended crowns: {row[0]},  crown_id: {row[1]}"
            #         )

            logger.info(
                "Clear selection and delete temporary layers, BEFORE moving to the next crown.."
            )
            lyr_list = [
                "point_lyr",
                "selected_polygon",
                tmp_crown_lyr,
                tmp_thiessen_lyr,
                tmp_split_crown_lyr,
                tmp_selected_points,
            ]

            lyr_list = [lyr for lyr in lyr_list if au.exists_and_has_features(lyr)]

            # clear and delete
            for lyr in lyr_list:
                arcpy.SelectLayerByAttribute_management(lyr, "CLEAR_SELECTION")
                arcpy.Delete_management(lyr)

            # solely clear selection (DO NOT DELETE)
            if au.exists_and_has_features(point_layer):
                arcpy.SelectLayerByAttribute_management(point_layer, "CLEAR_SELECTION")
            if au.exists_and_has_features(polygon_layer):
                arcpy.SelectLayerByAttribute_management(
                    polygon_layer, "CLEAR_SELECTION"
                )

    # reset extent
    env.extent = area_extent


def split_per_nb(
    gdb_stems, neighbourhood_list, municipality, spatial_reference, round, area_extent
):
    """_summary_

    Parameters
    ----------
    gdb_stems : _type_
        _description_
    neighbourhood_list : _type_
        _description_
    municipality : _type_
        _description_
    spatial_reference : _type_
        _description_
    round : _type_
        _description_
    """
    logger = logging.getLogger(__name__)
    logger.info(
        f"Split Case 2 treecrowns for <{municipality}> municipality using a Voronoi diagram."
    )

    from pathlib import Path

    interim_path = Path(gdb_stems).parent

    # Detect trees per neighbourhood
    for n_code in neighbourhood_list:
        logger.info("-------------------------------------------------------------")
        logger.info("CASE 2: SPLIT CROWNS FOR NEIGHBOURHOOD <<{}>>".format(n_code))
        logger.info("-------------------------------------------------------------")

        # workspace settings
        env.overwriteOutput = True
        env.outputCoordinateSystem = arcpy.SpatialReference(spatial_reference)

        # ------------------------------------------------------ #
        # Dynamic Path Variables
        # ------------------------------------------------------ #

        # input data
        filegdb_path = os.path.join(
            interim_path, "geo_relation", "round_" + str(round) + "_b" + n_code + ".gdb"
        )
        au.createGDB_ifNotExists(filegdb_path)
        v_raw_stems = os.path.join(gdb_stems, "stems_in_situ")
        v_crowns_c2 = os.path.join(filegdb_path, "crowns_c2")

        # output data
        v_crowns_c2_split = os.path.join(filegdb_path, "crowns_c2_split")
        if arcpy.Exists(v_crowns_c2_split):
            logger.info(f"Crowns already split for neighbourhood: {n_code}. SKIP.")
            return

        # arcpy.Delete_management(v_crowns_c2_split)
        # set environment
        env.overwriteOutput = True
        env.outputCoordinateSystem = arcpy.SpatialReference(spatial_reference)
        env.workspace = filegdb_path

        voronoi(
            polygon_layer=v_crowns_c2,
            point_layer=v_raw_stems,
            filegdb_path=filegdb_path,
            v_crowns_c2_split=v_crowns_c2_split,
            area_extent=area_extent,
        )

        logger.info("Done splitting crowns for neighbourhood: {}".format(n_code))

        # clear selection of all layers
        active_layers = [
            v_raw_stems,
            v_crowns_c2,
            v_crowns_c2_split,
        ]

        active_layers = [
            lyr for lyr in active_layers if au.exists_and_has_features(lyr)
        ]
        for lyr in active_layers:
            arcpy.SelectLayerByAttribute_management(lyr, "CLEAR_SELECTION")

    logger.info("Done splitting Crowns for: {}".format(neighbourhood_list))
    logger.info("Done splitting Crowns for: {}".format(neighbourhood_list))


def split_study_area(filegdb_path, v_raw_stems, spatial_reference, area_extent):
    """_summary_

    Parameters
    ----------
    filegdb_path : _type_
        _description_
    v_raw_stems : _type_
        _description_
    spatial_reference : _type_
        _description_
    """
    logger = logging
    # workspace settings
    env.overwriteOutput = True
    env.outputCoordinateSystem = arcpy.SpatialReference(spatial_reference)

    # ------------------------------------------------------ #
    # Dynamic Path Variables
    # ------------------------------------------------------ #

    v_crowns_c2 = os.path.join(filegdb_path, "crowns_c2")

    # output data
    v_crowns_c2_split = os.path.join(filegdb_path, "crowns_c2_split")
    if arcpy.Exists(v_crowns_c2_split):
        logger.info("Crowns already split. SKIP.")
        return

    # set environment
    env.overwriteOutput = True
    env.outputCoordinateSystem = arcpy.SpatialReference(spatial_reference)
    env.workspace = filegdb_path

    logger.info("--------------------")
    logger.info("CASE 2: SPLIT CROWNS")
    logger.info("--------------------")

    voronoi(
        polygon_layer=v_crowns_c2,
        point_layer=v_raw_stems,
        filegdb_path=filegdb_path,
        v_crowns_c2_split=v_crowns_c2_split,
        area_extent=area_extent,
    )

    # clear selection of all layers
    active_layers = [
        v_raw_stems,
        v_crowns_c2,
        v_crowns_c2_split,
    ]

    active_layers = [lyr for lyr in active_layers if au.exists_and_has_features(lyr)]
    for lyr in active_layers:
        arcpy.SelectLayerByAttribute_management(lyr, "CLEAR_SELECTION")

    logger.info("Done splitting crown.")


if __name__ == "__main__":
    pass
