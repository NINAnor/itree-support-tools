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
from src.config.config import load_catalog, load_parameters
from src.config.logger import setup_logging
from src.attributes.overlay_attributes import neighbourhood_stem, neighbourhood_crown
from src.attributes import tree_attributes
from src.attributes import (
    AdminAttributes,
    InsituAttributes,
    GeometryAttributes,
    RuleAttributes,
)
from src.utils import arcpy_utils as au


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


# recompute pollution_zone


if __name__ == "__main__":
    """Load data from raw to interim."""

    # set up logger
    setup_logging()
    logger = logging.getLogger(__name__)

    # input
    # input("Manually join stem_in_situ attributes to crowns. Press Enter to continue...")

    # load data
    (
        input_gdb,
        fc_crowns_insitu,
        fc_crowns_all,
        fc_stems,
        fc_neighbourhood,
        gdb_overlay,
    ) = load_data()

    # ALL CROWNS
    # ------------ GET CROWN ID ------------ #
    # 1. Calc nb_code
    if au.check_isNull(fc_crowns_all, "nb_code", "TEXT"):
        neighbourhood_crown(fc_crowns_all, gdb_overlay, fc_neighbourhood)

    # 2. Calc ID (from nb_code) for all crowns!
    if au.check_isNull(fc_crowns_all, "crown_id", "TEXT"):
        AdminAttribute = AdminAttributes(input_gdb, fc_crowns_all, fc_stems)
        AdminAttribute.attr_crownID("nb_code")

    # ------------ TREE HEIGHT ------------- #
    if au.check_isNull(fc_crowns_all, "total_tree_heigth", "FLOAT"):
        # init Class
        RuleAttribute = RuleAttributes(input_gdb, fc_crowns_all)
        # TREE HEIGHT (first!) (height_origin, height_total_tree)
        RuleAttribute.attr_ruleHeight()

    # ------------ CROWN AREA ------------- #
    if au.check_isNull(fc_crowns_all, "crown_area", "FLOAT"):
        # init Class
        GeometryAttribute = GeometryAttributes(input_gdb, fc_crowns_all, fc_stems)
        GeometryAttribute.attr_crownArea()

    # ------------ POLLUTION ZONE ---------- #
    if au.check_isNull(fc_crowns_all, "pollution_zone", "TEXT"):
        input(
            "MANUALLY: Add pollution_zone to crowns.\
            \n - download pollution raster\
            \n - reproject to correct utm zone\
            \n - extract values to point (crowns_xy) \
            \n - check that all crowns have a value \
            \n - export table to Excel (target_municipality)\
            \n Press Enter to continue..."
        )


# --------------------------------------------------------------------------- #
# REGISTERED TREES
# neighbourhood_stem(fc_stems, fc_crowns_insitu, gdb_overlay, fc_neighbourhood)
# join crownid to stem

# init class to calculate attributes
# AdminAttribute = AdminAttributes(input_gdb, fc_crowns_insitu, fc_stems)
# InsituAttribute = InsituAttributes(input_gdb, fc_crowns_insitu)
# GeometryAttribute = GeometryAttributes(input_gdb, fc_crowns_insitu, fc_stems)
# RuleAttribute = RuleAttributes(input_gdb, fc_crowns_insitu)
