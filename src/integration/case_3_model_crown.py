# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------- #
# Name: template.py
# Date: 2023-07-27
# Description:
# Author: Willeke A'Campo
# Dependencies:
# --------------------------------------------------------------------------- #

import logging
import os

import arcpy
from arcpy import env

from src import ADMIN_GDB, INTERIM_PATH, MUNICIPALITY, SPATIAL_REFERENCE, RuleAttributes
from src import arcpy_utils as au
from src import logger

# # Export trees with estimated crown
# l_trees = arcpy.MakeFeatureLayer_management (v_stems_c3, "trees_layer")
# query = "crown_radius IS NOT NULL"
# arcpy.FeatureClassToFeatureClass_conversion(
#     in_features= l_trees,
#     out_path = filegdb_path,
#     out_name = out_name,
#     where_clause = query
# )

# # 6. manually - split crowns with more than one temp_trees_with_modelled_crown
# #v_crowns_split_geometry = "temp_cd_3_singlepart_join4"

# # 7. join with ID of tree crowns (from those with modelled crown and suitable for i-Tree)
# #l_trees_crowns = arcpy.MakeFeatureLayer_management ("temp_trees_with_modelled_crown", "trees_layer2")
# #arcpy.SelectLayerByAttribute_management(l_trees_crowns, "NEW_SELECTION", "suitable_for_itree_spec_dbh = 1")

# #v_crowns_modelled = "estimated_crowns_for_BYM_OB"
# #arcpy.SpatialJoin_analysis(v_crowns_split_geometry, l_trees_crowns, v_crowns_modelled, "JOIN_ONE_TO_ONE", "KEEP_ALL")

# # delete unwanted fields, adjust manually - only keep TREE_ID
# #arcpy.DeleteField_management(v_crowns_modelled, drop_field="TARGET_FID;AnleggNavn;Foreslått_tiltak;Stammediameter;Stammeomkrets;Stammeform;Livsfase;Plantedato;Stammeskade;Råte;Hulrom;Sopplegeme;Sykdom;Saltskade;Mekanisk__Brekkasjerisiko_;Vekt;Skadepotensiale;TiltakDato;Skader_reg_i_AT;Bydel;RiskRegDato;NSkode;RegDato;Registrant;Rotskade;Vitalitet;OpprettetAv;OpprettetDato;EndretAv;EndretDato;Risiko;Sår_Ø5cm;Tilleggskommentar;Kronediameter;TRE_ID_NR;Kronestabilisering;Kronestabilisering_Installasjonsdato;Bevaringsstatus;Grenbrekkasje;Treslag;Vaksinasjonsnavn;Vaksinasjonsdato;Vaksinasjon_utført_av;x;y;BotNavn_backup;Artsnavn_backup;diameter_from_perimeter;perimeter_from_diameter;diameter_diff;perimeter_diff;Stammediameter_backup;Stammeomkrets_backup;DBH_corr_cm;DBH_orig;DBH_comment;H;botnavn_corr;botnavn_corr2;botnavn_corr2_comment;artsnavn_corr1;artsnavn_corr2;artsnavn_botnavn_comment;artsnavn_corr3;botnavn_corr3;JOIN_ID;it_origin;it_ID;it_code;it_sc_name;it_co_name;it_genus;it_family;it_order;it_class;it_gr_form;it_p_ltype;it_ltype;it_gr_rate;it_longev;it_h;lc_ssb;CROWN_ID;MGBDIAM;BLD_DIST_1;BLD_DIST_2;BLD_DIST_3;BLD_DIR_1;BLD_DIR_2;BLD_DIR_3;CLE_CLASS;CLE_PERC;lc_ssb_hoved;lc_ssb_under;lc_ar5;lc_itree;H_origin;DBH_origin;CD_origin;N_S_WIDTH;E_W_WIDTH;WGS84_LON;WGS84_LAT;DBH_MEASURED;STREET_TREE;suitable_for_itree_spec_dbh;crown_width_itree;height_to_crown_base_itree;crown_height_itree;crown_radius_itree;temp_crown_radius")

# # 8. add CROWN_ID - 100.000 + OBJECTID
# #AddFieldIfNotexists(v_crowns_modelled, "CROWN_ID", "Long")
# #arcpy.CalculateField_management(v_crowns_modelled, "CROWN_ID", "[OBJECTID] + 100000")

# # 9. Add field for crown origin
# #AddFieldIfNotexists(v_crowns_modelled, "origin", "Text")
# #arcpy.CalculateField_management(v_crowns_modelled, "origin", '"estimated from DBH"')

# # 10. Compute MGBDIAM, POLY_AREA, PERIMETER
# v_crowns_modelled = "temp_correction_crowns_combined"
# v_circle = "temp_circumscribed_circle"
# arcpy.MinimumBoundingGeometry_management(v_crowns_modelled, v_circle, "CIRCLE", "NONE", "", "MBG_FIELDS")

# AddFieldIfNotexists(v_crowns_modelled, "MGBDIAM", "Double")
# join_and_copy(v_crowns_modelled, "CROWN_ID", v_circle, "CROWN_ID", ["MBG_Diameter"], ["MGBDIAM"])
# arcpy.Delete_management(v_circle)

# AddFieldIfNotexists(v_crowns_modelled, "POLY_AREA", "Double")
# AddFieldIfNotexists(v_crowns_modelled, "PERIMETER", "Double")
# arcpy.CalculateField_management(v_crowns_modelled, "POLY_AREA", "[Shape_Area]")
# arcpy.CalculateField_management(v_crowns_modelled, "PERIMETER", "[Shape_Length]")

# # 11. Compute N_S_WIDTH, E_W_WIDTH
# v_envelope = "temp_envelope"
# arcpy.MinimumBoundingGeometry_management(v_crowns_modelled, v_envelope, "ENVELOPE", "NONE", "", "MBG_FIELDS")

# AddFieldIfNotexists(v_envelope, "Angle", "Double")
# arcpy.CalculatePolygonMainAngle_cartography (v_envelope, "Angle", "GEOGRAPHIC")

# AddFieldIfNotexists(v_envelope, "N_S_WIDTH", "Double")
# AddFieldIfNotexists(v_envelope, "E_W_WIDTH", "Double")
# codeblock = """def calculateEnvelope(envelope_width, envelope_length, envelope_angle, computed_measure):
#     eps = 1e-2
#     if abs(envelope_angle+90) < eps:
#         if computed_measure == "N_S":
#             return envelope_length
#         elif computed_measure == "E_W":
#             return envelope_width
#         else:
#             return None
#     elif abs(envelope_angle) < eps:
#         if computed_measure == "N_S":
#             return envelope_width
#         elif computed_measure == "E_W":
#             return envelope_length
#         else:
#             return None
#     else:
#         return None
# """
# arcpy.CalculateField_management(v_envelope, "N_S_WIDTH", 'calculateEnvelope(!MBG_Width!, !MBG_Length!, !Angle!, "N_S")', "PYTHON_9.3", codeblock)
# arcpy.CalculateField_management(v_envelope, "E_W_WIDTH", 'calculateEnvelope(!MBG_Width!, !MBG_Length!, !Angle!, "E_W")', "PYTHON_9.3", codeblock)

# AddFieldIfNotexists(v_crowns_modelled, "N_S_WIDTH", "Double")
# AddFieldIfNotexists(v_crowns_modelled, "E_W_WIDTH", "Double")
# join_and_copy(v_crowns_modelled, "CROWN_ID", v_envelope, "CROWN_ID", ["N_S_WIDTH", "E_W_WIDTH"], ["N_S_WIDTH", "E_W_WIDTH"])
# arcpy.Delete_management(v_envelope)

# # 9. join with ALS estimated crowns
# #v_crowns_ALS = "crowns_NINA_segmented"
# #v_crowns_merged = "crowns_NINA_segmented_estimated"
# #arcpy.Merge_management([v_crowns_ALS, v_crowns_modelled], v_crowns_merged)

# # 10. join to i-Tree db
# #join_and_copy(v_trees, "TREE_ID", v_crowns_merged, "TREE_ID", ["CROWN_ID", "MGBDIAM", "N_S_WIDTH", "E_W_WIDTH", "origin"], ["CROWN_ID", "MGBDIAM", "N_S_WIDTH", "E_W_WIDTH", "CD_origin"])


def main(neighbourhood_list: list):
    print("make main script")

    logging.info(
        "Iterate over neighbourhoods and model crown geometry for CASE 3 stems)"
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

        filegdb_path = os.path.join(
            INTERIM_PATH, "geo_relation", "round_1_b" + n_code + ".gdb"
        )

        # input
        v_stems_c3 = os.path.join(filegdb_path, f"stems_c3")
        v_crowns_raw = os.path.join(
            INTERIM_PATH, "input_crowns.gdb", "b_" + n_code + "_kroner"
        )

        # temp
        v_buffer = os.path.join(filegdb_path, "tmp_c3_buffer")
        v_erase = os.path.join(filegdb_path, "tmp_c3_erase_ALScrown")
        v_dissolve = os.path.join(filegdb_path, "tmp_c3_dissolve")

        # output
        out_name = "crowns_c3_modelled"
        v_crowns_c3_modelled = os.path.join(filegdb_path, out_name)

        # workspace settings
        env.overwriteOutput = True
        env.outputCoordinateSystem = arcpy.SpatialReference(SPATIAL_REFERENCE)
        # env.workspace = filegdb_path

        # compute buffer based on crown_radius
        if arcpy.Exists(v_crowns_c3_modelled):
            arcpy.Delete_management(v_crowns_c3_modelled)
            logging.info("v_crowns_c3_modelled already exists. Delete file")

        # init class
        rule_attribute = RuleAttributes(filegdb_path, v_stems_c3)
        rule_attribute.attr_ruleCrown()

        # model crown by creating a buffer with radius = crown_radius
        attr_field = "crown_radius"
        arcpy.Buffer_analysis(v_stems_c3, v_buffer, attr_field, "", "", "ALL")

        # subtract ALS crowns from buffer
        arcpy.Erase_analysis(v_buffer, v_crowns_raw, v_erase)

        # dissolve
        arcpy.Dissolve_management(v_erase, v_dissolve)

        # Convert to singlepart (Buffer tool creates one multipolygon object)
        arcpy.MultipartToSinglepart_management(v_dissolve, v_crowns_c3_modelled)

        # add fields to the new feature class
        au.addField_ifNotExists(v_crowns_c3_modelled, "geo_relation", "TEXT")
        arcpy.CalculateField_management(
            v_crowns_c3_modelled, "geo_relation", "'Case 3'", "PYTHON_9.3"
        )
        au.addField_ifNotExists(v_crowns_c3_modelled, "bydelnummer", "TEXT")
        arcpy.CalculateField_management(
            v_crowns_c3_modelled, "bydelnummer", str(n_code), "PYTHON_9.3"
        )

        # delete temporary files
        # files = [v_buffer, v_erase, v_dissolve]
        # for file in files:
        # arcpy.Delete_management(file)


def all(filegdb_path, v_crowns_all):
    # ------------------------------------------------------ #
    # Dynamic Path Variables
    # ------------------------------------------------------ #

    # input
    v_stems_c3 = os.path.join(filegdb_path, f"stems_c3")

    # temp
    v_buffer = os.path.join(filegdb_path, "tmp_c3_buffer")
    v_erase = os.path.join(filegdb_path, "tmp_c3_erase_ALScrown")
    v_dissolve = os.path.join(filegdb_path, "tmp_c3_dissolve")
    v_singlepart = os.path.join(filegdb_path, "tmp_c3_singlepart")

    # output
    out_name = "crowns_c3_modelled"
    v_crowns_c3_modelled = os.path.join(filegdb_path, out_name)

    # workspace settings
    env.overwriteOutput = True
    env.outputCoordinateSystem = arcpy.SpatialReference(SPATIAL_REFERENCE)
    env.workspace = filegdb_path

    # compute buffer based on crown_radius
    if arcpy.Exists(v_crowns_c3_modelled):
        arcpy.Delete_management(v_crowns_c3_modelled)
        logging.info("v_crowns_c3_modelled already exists. Delete file")

    # init class
    rule_attribute = RuleAttributes(filegdb_path, v_stems_c3)
    rule_attribute.attr_ruleCrown()

    # model crown by creating a buffer with radius = crown_radius
    attr_field = "crown_radius"
    arcpy.Buffer_analysis(v_stems_c3, v_buffer, attr_field, "", "", "ALL")

    # subtract ALS crowns from buffer
    arcpy.Erase_analysis(v_buffer, v_crowns_all, v_erase)

    # dissolve
    arcpy.Dissolve_management(v_erase, v_dissolve)

    # Convert to singlepart (Buffer tool creates one multipolygon object)
    arcpy.MultipartToSinglepart_management(v_dissolve, v_crowns_c3_modelled)

    # add fields to the new feature class
    au.addField_ifNotExists(v_crowns_c3_modelled, "geo_relation", "TEXT")
    au.calculateField_ifEmpty(v_crowns_c3_modelled, "geo_relation", "'Case 3'")

    # delete temporary files
    files = [v_buffer, v_erase, v_dissolve, v_singlepart]
    for file in files:
        arcpy.Delete_management(file)


if __name__ == "__main__":
    # setup logger
    logger.setup_logger(logfile=True)
    logger = logging.getLogger(__name__)

    # admin
    kommune = MUNICIPALITY

    # neighbourhood list
    neighbourhood_path = os.path.join(ADMIN_GDB, "bydeler")
    n_field_name = "bydelnummer"
    neighbourhood_list = au.get_neighbourhood_list(neighbourhood_path, n_field_name)
    neighbourhood_list.sort()
    print(neighbourhood_list)

    round = 1
    main(neighbourhood_list, round)
