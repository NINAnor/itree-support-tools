"""
Code adapted from https://github.com/zofie-cimburova/i-Tree-Eco/blob/main/crown_light_exposure.py 
COPYRIGHT:    (C) 2022 by Zofie Cimburova

Please backup your input data before the analysis.
In some rare cases, ArcGIS may corrupt the input data if
the analysis ends with error.
"""

import os
import random
import string

import arcpy
from arcpy import env

# TODO load spatial_reference from parameters.yaml
# TODO load data_paths from catalog.yaml
# from src import SPATIAL_REFERENCE, INTERIM_PATH


## Approx. 3.6 s / tree
# Check if field exists
def FieldExist(featureclass, fieldname):
    fieldList = arcpy.ListFields(featureclass, fieldname)
    fieldCount = len(fieldList)

    if fieldCount == 1:
        return True
    else:
        return False


# Create a random temporary name
def tempname(length):
    characters = string.ascii_letters + string.digits
    suffix = "".join(random.choice(characters) for i in range(length))
    tempname = "tmp_" + suffix
    return tempname


# add src folder as AddOn in ArcGIS Pro and run from ArcGIS Pro Python window
arcpy.AddMessage("Running crown light exposure script...")
filegdb_path = os.path.join(
    INTERIM_PATH, "itree_attributes", "itree_tree_cle_batch.gdb"
)
arcpy.AddMessage("File geodatabase path: " + filegdb_path)

# ==============================================================
# Workspace settings
# ==============================================================
env.overwriteOutput = True
env.workspace = filegdb_path
# env.workspace = r"in_memory"

# ==============================================================
# Input data
# ==============================================================
# Must be all in the same coordinate system
n_code = "180401"
arcpy.AddMessage("Processing Neighbourhood: " + n_code)
# Trees (polygons, must contain
# unique ID attribute named "TREE_ID")
# v_trees_poly = arcpy.GetParameterAsText(0)

v_trees_poly = os.path.join(filegdb_path, "itree_crowns_" + n_code)
arcpy.Delete_management(["tree_crowns_layer", "tree_trunks_layer"])
l_crowns = arcpy.MakeFeatureLayer_management(v_trees_poly, "tree_crowns_layer")
l_trees_poly = arcpy.MakeFeatureLayer_management(
    v_trees_poly,
    "tree_crowns_layer",
)

# Trees (points, must contain
# attribute with cown diameter named "CD",
# unique ID attribute named "TREE_ID")
# v_trees_pts = arcpy.GetParameterAsText(1)

v_trees_pts = os.path.join(filegdb_path, "itree_stems_" + n_code)
l_trees_pts = arcpy.MakeFeatureLayer_management(
    v_trees_pts,
    "tree_trunks_layer",
)

# Buildings (polygons)
# v_buildings = arcpy.GetParameterAsText(2)
# kristiansand
# v_buildings = r"P:\152022_itree_eco_ifront_synliggjore_trars_rolle_i_okosyst\data\kristiansand\general\kristiansand_basisdata.gdb\fkb_bygning_omrade"

# bodo
v_buildings = r"C:\Data\offline_data\trekroner\data\bodo\general\bodo_basisdata.gdb\fkb_bygning_omrade"

# Digital surface model
# r_dsm = arcpy.GetParameterAsText(3)
# r_dsm = r"P:\152022_itree_eco_ifront_synliggjore_trars_rolle_i_okosyst\data\kristiansand\general\kristiansand_hoydedata.gdb\dsm_dtm_025m_float"
r_dsm = r"P:\152022_itree_eco_ifront_synliggjore_trars_rolle_i_okosyst\data\bodo\general\bodo_hoydedata.gdb\dsm_dtm_05m_float_utm33"

# Attributes
a_ID = "tree_id"  # tree ID (links tree points and polygons)
a_CD = "crown_diam"  # crown diameter
a_CLE = "cle_perc"  # new attribute storing crown light exposure
a_H = "height_total_tree"
# ==============================================================
# Add fields to store crown light exposure values
# ==============================================================
if not FieldExist(v_trees_poly, a_CLE):
    arcpy.AddField_management(v_trees_poly, a_CLE, "Float")

# ==============================================================
# Prepare convex hulls of tree crowns (LINES)
# ==============================================================
# Polygons
v_hulls_poly = "tmp_hulls_poly_{}".format(tempname(4))
arcpy.MinimumBoundingGeometry_management(
    v_trees_poly,
    v_hulls_poly,
    geometry_type="CONVEX_HULL",
    group_option="NONE",
    group_field="",
    mbg_fields_option="NO_MBG_FIELDS",
)

# Polylines
v_hulls_line = "tmp_hulls_line_{}".format(tempname(4))
arcpy.PolygonToLine_management(
    v_hulls_poly,
    v_hulls_line,
    "IGNORE_NEIGHBORS",
)

# Compute perimeter length
a_peri = "CROWN_PERIM"
if not FieldExist(v_hulls_line, a_peri):
    arcpy.AddField_management(v_hulls_line, a_peri, "Float")

arcpy.AddGeometryAttributes_management(v_hulls_line, "LENGTH")
arcpy.CalculateField_management(v_hulls_line, a_peri, "!SHAPE_Length!")

# Convert to layer
l_hulls_line = arcpy.MakeFeatureLayer_management(v_hulls_line, "l_hulls_line")

arcpy.Delete_management(v_hulls_poly)

# ==============================================================
# Iterate over trees (points)
# ==============================================================
cle_values = {}
n_trees = int(arcpy.GetCount_management(v_trees_pts)[0])

with arcpy.da.SearchCursor(
    v_trees_pts, ["SHAPE@", "SHAPE@XY", a_ID, a_CD, a_H]
) as cursor:
    i = 0
    for row in cursor:
        tree_id = row[2]
        tree_d = row[3]
        # insitu_height = row[4]

        prefix = "{}_{}".format(tempname(4), tree_id)

        # ==============================================================
        # Tree buffer
        # ==============================================================
        v_buffer = "{}_buf".format(prefix)
        arcpy.Buffer_analysis(
            row[0],
            v_buffer,
            str(tree_d),
        )

        # Save buffer extent
        buffer_extent = arcpy.Extent(
            row[0].extent.XMin - tree_d,
            row[0].extent.YMin - tree_d,
            row[0].extent.XMax + tree_d,
            row[0].extent.YMax + tree_d,
        )

        # ==============================================================
        # Select surrounding structures - vector
        # ==============================================================
        # Select all tree polygons that are not the analysed tree
        arcpy.SelectLayerByAttribute_management(
            l_trees_poly,
            "NEW_SELECTION",
            "{} <> '{}'".format(a_ID, tree_id),
        )

        # Surrounding trees within buffer
        v_surr_t = "{}_st".format(prefix)
        arcpy.Clip_analysis(l_trees_poly, v_buffer, v_surr_t)

        # Surrounding buildings within buffer
        v_surr_b = "{}_sb".format(prefix)
        arcpy.Clip_analysis(v_buildings, v_buffer, v_surr_b)

        # Merge surrounding trees + buildings within buffer
        v_surr_tb = "{}_stb".format(prefix)
        arcpy.Merge_management([v_surr_b, v_surr_t], v_surr_tb)

        arcpy.Delete_management(v_buffer)
        arcpy.Delete_management(v_surr_b)
        arcpy.Delete_management(v_surr_t)

        # If there are surrounding structures,
        # model the shadowed border
        n_surr = int(arcpy.GetCount_management(v_surr_tb)[0])
        v_hull_shadow = "{}_border_shadow".format(prefix)

        if n_surr > 0:
            # ==============================================================
            # Select surrounding structures - raster
            # ==============================================================
            r_surr_tb = "{}_surrounding_structure_r".format(prefix)

            # Clip raster with surrounding trees and buildings
            rectangle = "{} {} {} {}".format(
                buffer_extent.XMin,
                buffer_extent.YMin,
                buffer_extent.XMax,
                buffer_extent.YMax,
            )
            try:
                arcpy.Clip_management(
                    r_dsm,
                    rectangle,
                    r_surr_tb,
                    v_surr_tb,
                    "",
                    "ClippingGeometry",
                )
            except arcpy.ExecuteError:
                # If the analysis fails, set CLE to NoData
                cle_perc = -999
                cle_values[str(tree_id)] = cle_perc

                # Progress
                i = i + 1
                arcpy.AddMessage(
                    "{:.2f}% TREE_ID = {} CLE = {}".format(
                        i / float(n_trees) * 100, tree_id, cle_perc
                    )
                )

                continue

            arcpy.Delete_management(v_surr_tb)

            # If any pixels in raster are higher than the tree
            x, y = row[1]

            tree_h = (
                arcpy.GetCellValue_management(r_dsm, "{} {}".format(x, y))
                .getOutput(0)
                .replace(",", ".")
            )
            arcpy.AddMessage("Tree height:" + str(tree_h))
            if tree_h == "NoData":
                tree_h = row[4]
                arcpy.AddMessage("Tree height (in situ):" + str(tree_h))
            else:
                tree_h = float(tree_h)

            max_h = (
                arcpy.GetRasterProperties_management(r_surr_tb, "MAXIMUM")
                .getOutput(0)
                .replace(",", ".")
            )
            arcpy.AddMessage("Tree surrounding maximum pixels:" + str(max_h))
            if max_h == "NoData":
                max_h = 0
            else:
                max_h = float(max_h)

            if max_h >= tree_h:
                # ==============================================================
                # Select surrounding structures higher than the tree
                # ==============================================================
                # Threshold surrounding trees and buildings
                r_surr_tb_higher = "{}_stbh_r".format(prefix)
                arcpy.gp.Reclassify_sa(
                    r_surr_tb,
                    "Value",
                    "0 {} NODATA;{} 10000 1".format(tree_h, tree_h),
                    r_surr_tb_higher,
                    "DATA",
                )
                arcpy.Delete_management(r_surr_tb)

                # Vectorise thresholded trees and buildings
                v_surr_tb_higher = "{}_stbh".format(prefix)
                arcpy.RasterToPolygon_conversion(
                    r_surr_tb_higher,
                    v_surr_tb_higher,
                )
                arcpy.Delete_management(r_surr_tb_higher)

                # If there are no higher surrounding structures
                n_higher = int(arcpy.GetCount_management(v_surr_tb_higher)[0])

                if n_higher == 0:
                    # CLE
                    cle_perc = 1.0
                    cle_values[str(tree_id)] = cle_perc

                    arcpy.Delete_management(v_surr_tb_higher)

                    # Progress
                    i = i + 1
                    arcpy.AddMessage(
                        "{:.2f}% TREE_ID = {} CLE = {}".format(
                            i / float(n_trees) * 100, tree_id, cle_perc
                        )
                    )

                    continue

                # ==============================================================
                # Construct shadow
                # ==============================================================
                # Add attribute storing the ID of the analysed tree
                arcpy.AddField_management(v_surr_tb_higher, a_ID, "TEXT")

                arcpy.CalculateField_management(v_surr_tb_higher, a_ID, f"'{tree_id}'")

                # Add attribut storing the ID of the surrounding structure
                arcpy.AddField_management(v_surr_tb_higher, "OBST_ID", "Long")
                arcpy.CalculateField_management(
                    v_surr_tb_higher,
                    "OBST_ID",
                    "!OBJECTID!",
                )

                # Convert surrounding structures to points
                v_surr_tb_pt = "{}_stbp".format(prefix)
                arcpy.FeatureVerticesToPoints_management(
                    v_surr_tb_higher,
                    v_surr_tb_pt,
                    point_location="ALL",
                )
                arcpy.Delete_management(v_surr_tb_higher)

                # Add the tree point to the points of surrounding structures
                cursor2 = arcpy.da.InsertCursor(
                    v_surr_tb_pt,
                    ["SHAPE@", "OBST_ID", a_ID, "ORIG_FID", "gridcode", "Id"],
                )
                for j in range(1, n_higher + 1):
                    x, y = row[1]
                    cursor2.insertRow([arcpy.Point(x, y), j, tree_id, j, 1, j])
                del cursor2

                # Compute shadow = hull around the the points of
                # surrounding structures
                v_shadow = "{}_shadow".format(prefix)
                arcpy.MinimumBoundingGeometry_management(
                    v_surr_tb_pt,
                    v_shadow,
                    geometry_type="CONVEX_HULL",
                    group_option="LIST",
                    group_field="OBST_ID",
                    mbg_fields_option="NO_MBG_FIELDS",
                )
                arcpy.Delete_management(v_surr_tb_pt)

                # ==============================================================
                # Clip the tree crown with the shadow
                # ==============================================================
                # Select the analysed hull (line)
                arcpy.SelectLayerByAttribute_management(
                    l_hulls_line,
                    "NEW_SELECTION",
                    "{} = '{}'".format(a_ID, tree_id),
                )

                # Clip the analysed hull with the shadow
                arcpy.Clip_analysis(l_hulls_line, v_shadow, v_hull_shadow)
                arcpy.Delete_management(v_shadow)

            else:
                arcpy.Delete_management(r_surr_tb)

        else:
            arcpy.Delete_management(v_surr_tb)

        # ==============================================================
        # Compute CLE
        # ==============================================================
        if arcpy.Exists(v_hull_shadow):
            # dissolve borders
            v_hull_shadow_d = os.path.join(filegdb_path, "{}_md".format(prefix))
            arcpy.Dissolve_management(
                v_hull_shadow,
                v_hull_shadow_d,
                "",
                [[a_peri, "FIRST"]],
            )
            arcpy.Delete_management(v_hull_shadow)

            # compute percentage
            arcpy.AddField_management(v_hull_shadow_d, a_CLE, "Float")
            arcpy.CalculateField_management(
                v_hull_shadow_d,
                a_CLE,
                "!Shape!.Length/!FIRST_CROWN_PERIM!",
                "PYTHON_9.3",
            )

            cle_perc = -999
            cursor3 = arcpy.da.SearchCursor(v_hull_shadow_d, [a_CLE])
            for row3 in cursor3:
                cle_perc = 1 - row3[0]

            arcpy.Delete_management(v_hull_shadow_d)

        # If there are NO surrounding structures
        else:
            cle_perc = 1.0

        # CLE
        cle_values[str(tree_id)] = cle_perc

        # Progress
        i = i + 1
        arcpy.AddMessage(
            "{:.2f}% TREE_ID = {} CLE = {}".format(
                i / float(n_trees) * 100, tree_id, cle_perc
            )
        )

# Delete convex hulls
arcpy.Delete_management(v_hulls_line)

# ==============================================================
# Update attribute table with CLE values
# ==============================================================
with arcpy.da.UpdateCursor(v_trees_poly, [a_ID, a_CLE]) as cursor:
    for row in cursor:
        tree_id = str(row[0])
        row[1] = cle_values[tree_id]
        cursor.updateRow(row)

# ==============================================================


# ==============================================================
# Field calculator code blocks
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
