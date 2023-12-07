# prepare for attribute computation
# TODO automate pre-processing

# input("Check if stem layer contains XY coord. Press Enter to continue...")
# input("MANUALLY Join stem to crown (one-to-one, contains, join_count = 1))")
# check if crown contains stem attr.

# Step 1 Overla analaysis
# subroutine overlay_attributes.py

# TODO compute attributes necessary for extrapolation
# TODO compute attributes necessary for itree-eco model

# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------- #
# Name: prepare_data.py
# Date: 2023-10-19
# Description: Prepare data for itree-eco analysis and extrapolation
# Author: Willeke A'Campo
# Dependencies: ArcGIS Pro 3.0+, Spatial Analyst
# --------------------------------------------------------------------------- #

import logging
import os

import src.utils.decorators as dec
from src.attributes.classes import AdminAttributes, GeometryAttributes, RuleAttributes
from src.attributes.overlay_attributes import neighbourhood_crown, neighbourhood_stem
from src.config.config import load_catalog, load_parameters
from src.config.logger import setup_logging
from src.utils import arcpy_utils as au


def check_and_perform(attribute, type, action):
    if au.check_isNull(fc_crowns_all, attribute, type):
        action()


@dec.timer
def load_data():
    # load catalog
    logger = logging.getLogger(__name__)
    logger.info("Loading catalog...")
    catalog = load_catalog()
    logger.info("Loading parameters...")
    parameters = load_parameters()

    # set parameters
    municipality = parameters["municipality"]
    spatial_reference = parameters["spatial_reference"][municipality]

    # input data
    fc_neighbourhood = catalog["neighbourhood"]["filepath"]
    key_neighbourhood = catalog["neighbourhood"]["key"]  # field name

    input_gdb = catalog["attr_input"]["filepath"]
    fc_crowns_insitu = os.path.join(input_gdb, catalog["attr_input"]["fc"][0])
    fc_crowns_all = os.path.join(input_gdb, catalog["attr_input"]["fc"][1])
    fc_stems = os.path.join(input_gdb, catalog["attr_input"]["fc"][2])

    # output
    gdb_overlay = catalog["attr_overlay"]["filepath"]
    return (
        input_gdb,
        fc_crowns_insitu,
        fc_crowns_all,
        fc_stems,
        fc_neighbourhood,
        gdb_overlay,
    )


@dec.timer
def crown_polygon_attributes(
    input_gdb, fc_crowns_all, fc_stems, gdb_overlay, fc_neighbourhood
):
    # ------------ GET CROWN ID ------------ #
    # 1. Calc nb_code
    check_and_perform(
        "nb_code",
        "TEXT",
        lambda: neighbourhood_crown(fc_crowns_all, gdb_overlay, fc_neighbourhood),
    )

    # 2. Calc ID (from nb_code) for all crowns!
    check_and_perform(
        "crown_id",
        "TEXT",
        lambda: AdminAttributes(input_gdb, fc_crowns_all, fc_stems).attr_crownID(
            "nb_code"
        ),
    )

    # ------------ TREE HEIGHT ------------- #
    check_and_perform(
        "total_tree_heigth",
        "FLOAT",
        lambda: RuleAttributes(input_gdb, fc_crowns_all).attr_ruleHeight(),
    )

    # ------------ CROWN AREA ------------- #
    check_and_perform(
        "crown_area",
        "FLOAT",
        lambda: GeometryAttributes(input_gdb, fc_crowns_all, fc_stems).attr_crownArea(),
    )

    # ------------ POLLUTION ZONE ---------- #
    # TODO automate this step (see below)
    input(
        "MANUALLY: Add pollution_zone to crowns.\
            \n - download pollution raster\
            \n - reproject to correct utm zone\
            \n - extract values to point (crowns_xy) \
            \n - check that all crowns have a value \
            \n - export table to Excel (target_municipality)\
            \n Press Enter to continue..."
    )


@dec.timer
def itree_point_attributes(
    input_gdb,
    fc_crowns_insitu,
    fc_stems,
    fc_neighbourhood,
    gdb_overlay,
    gdb_tree_attributes,
    gdb_building_distance,
    gdb_cle,
):
    # ------------ GET CROWN ID ------------ #
    neighbourhood_stem(fc_stems, fc_crowns_insitu, gdb_overlay, fc_neighbourhood)

    # ------------ INIT CLASSES ------------ #
    AdminAttribute = AdminAttributes(input_gdb, fc_crowns_insitu, fc_stems)
    InsituAttribute = InsituAttributes(input_gdb, fc_crowns_insitu)
    GeometryAttribute = GeometryAttributes(input_gdb, fc_crowns_insitu, fc_stems)
    RuleAttribute = RuleAttributes(input_gdb, fc_crowns_insitu)

    # ------------ PIPELINE 1: OVERLAY ANALYSIS ------------ #
    from src.attributes.overlay import pipeline

    # interim DB: gdb_overlay
    # itree-support-tools/interim/attributes/attr_overlay.gdb
    pipeline.overlay(
        v_stem_path=fc_stems,
        v_crown_path=fc_crowns_insitu,
        filegdb_path=gdb_overlay,
        v_neighbourhoods=fc_neighbourhood,
        v_area_data=v_area_data,
        v_property_data=v_property_data,
    )

    # ------------ PIPELINE 2: TREE ATTRIBUTES ------------ #
    from src.attributes.tree import pipeline

    # interim DB: gdb_tree_attributes
    # itree-support-tools/interim/attributes/attr_tree.gdb
    pipeline.tree(gdb_tree_attributes, fc_crowns_insitu)

    # ------------ MODULE 1: BUILDING DISTANCE ------------ #
    from src.attributes import distance_to_building as dtb

    # interim DB: attr_building_distance.gdb
    dtb.distance_to_building(
        gdb_building_distance, v_stem_path, v_crown_path, v_residential_buildings
    )

    # ------------ MODULE 2: CROWN LIGHT EXPOSURE (CLE) ----#
    # (C) 2022 by Zofie Cimburova

    # interim DB: attr_cle.gdb
    logger.info("Run CROWN LIGHT EXPOSURE from separate script")
    logger.info("see src/attributes/crown_light_exposure.py")
    logger.info(f"Run to a separate gdb: {gdb_cle}")
    logger.info(
        "PLEASE BACKUP YOUR DATA BEFORE THIS ANALYSIS, DATA CORRUPTION MAY OCCUR."
    )

    return


if __name__ == "__main__":
    """Load data from raw to interim."""

    # set up logger
    setup_logging()
    logger = logging.getLogger(__name__)

    # input
    input("Manually join stem_in_situ attributes to crowns. Press Enter to continue...")

    # load project data
    (
        input_gdb,
        fc_crowns_insitu,
        fc_crowns_all,
        fc_stems,
        fc_neighbourhood,
        gdb_overlay,
    ) = load_data()

    # auxillary datasets
    # TODO move to catalog.yaml
    v_neighbourhoods = os.path.join(ADMIN_GDB, "bydeler")
    v_area_data = r"path/to/%municipality%_arealdata.gdb"
    v_property_data = r"path/to/municipality_eiendom.gdb"
    v_residential_buildings = (
        r"path/to/%municipality%_arealdata.gdb/fkb_boligbygg_omrade"
    )

    # set env workspace
    env.workspace = input_gdb

    load_data()
    crown_polygon_attributes(
        input_gdb, fc_crowns_all, fc_stems, gdb_overlay, fc_neighbourhood
    )
    itree_point_attributes(
        input_gdb, fc_crowns_insitu, fc_stems, gdb_overlay, fc_neighbourhood
    )
