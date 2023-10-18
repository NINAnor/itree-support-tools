import logging
import os

import arcpy

from src import arcpy_utils as au


class GeometryAttributes:
    """
    A class for computing administrative attributes.

    Attributes:
    -----------
    path : str
        path to the filegdb containing the crown and top feature classes
    crown_filename : str
        filename of the crown feature class
    top_filename : str
        filename of the top feature class

    Methods:
    --------
    - attr_crownArea(self)
    - attr_crownVolume(self)
    - attr_enclosingCircle(self, keep_temp: bool)
    - attr_convexHull(self, keep_temp: bool)
    - attr_envelope(self, keep_temp: bool)
    """

    def __init__(
        self, path: str, crown_filename: str, point_filename: str, logger=None
    ):
        self.path = path
        self.crown_filename = crown_filename
        self.top_filename = point_filename
        self.logger = logger or logging.getLogger(__name__)

    def attr_crownArea(self):
        """
        Calculates the crown area and perimeter attributes and adds them to the crown feature class.

        -----------------------------------
        crown_area (SHAPE_Area): the area of the resulting polygon
        crown_peri (SHAPE_Length): the perimeter of the resulting polygon
        outlier_CA: classifies the tree crown in normal (0), mild outlier (1) or extreme outlier (2).
            - normal (0) if crown area <= 250 m2
            - mild outlier (1) if crown area > 250 m2
            - extreme outlier (2) if crown area > 350 m2
        -----------------------------------
        """
        self.logger.info("\tATTRIBUTE | crown_area:")
        self.logger.info(
            f"\tComputing the crown area by using the polygon shape area... "
        )
        self.logger.info("\tATTRIBUTE | crown_peri:")
        self.logger.info(
            f"\tComputing the crown perimeter by using the shape length... "
        )

        # Get the linear units of the feature layer's spatial reference
        linear_units = arcpy.Describe(
            self.crown_filename
        ).spatialReference.linearUnitName

        # Calculate the area of each feature based on its geometry and write the result to the crown_area field
        if linear_units == "Meter":
            self.logger.info("\tThe linear unit to calculate the area is Meter")
            expression_area = "float(!SHAPE.area@squaremeters!)"
            expression_perimeter = "float(!SHAPE.length@meters!)"
        else:
            conversion_factor = arcpy.Describe(
                self.crown_filename
            ).spatialReference.metersPerUnit
            expression_area = "float(!SHAPE.area@squaremeters!) * {}".format(
                conversion_factor
            )
            expression_perimeter = "float(!SHAPE.length@meters!) * {}".format(
                conversion_factor
            )

        field_list = ["crown_area", "crown_peri"]
        for field in field_list:
            au.addField_ifNotExists(self.crown_filename, field, "FLOAT")

        au.addField_ifNotExists(self.crown_filename, "outlier_CA", "SHORT")

        au.calculateField_ifEmpty(self.crown_filename, "crown_area", expression_area)
        au.calculateField_ifEmpty(
            self.crown_filename, "crown_peri", expression_perimeter
        )

        if au.check_isNull(self.crown_filename, "outlier_CA") == True:
            with arcpy.da.UpdateCursor(
                self.crown_filename, ["crown_area", "outlier_CA"]
            ) as cursor:
                for row in cursor:
                    if row[0] <= 250:
                        row[1] = 0
                    elif row[0] > 250 and row[0] <= 350:
                        row[1] = 1
                    else:
                        row[1] = 2
                    cursor.updateRow(row)
        else:
            self.logger.info(
                f"\tAll rows in field are already populated. Exiting function."
            )

        au.round_fields_two_decimals(self.crown_filename, ["crown_area", "crown_peri"])

    def attr_crownVolume(self):
        """
        Adds the attribute 'tree_volume' (FlOAT) to the crown feature class.
        """

        au.addField_ifNotExists(self.crown_filename, "tree_volume", "FLOAT")
        # Calculate tree volume
        formula = str("tree volume =(1/3)π * (crown diameter/2)^2 * tree height")
        self.logger.info(
            f"\tComputing the crown volume by using the formula: \t{formula}"
        )

        expression = "(1.0/3.0) * math.pi * ( !crown_diam! /2.0 ) * ( !crown_diam! /2.0) * float(!height_total_tree!)"
        au.calculateField_ifEmpty(
            in_table=self.crown_filename,
            field="tree_volume",
            expression=expression,
        )

        au.round_fields_two_decimals(self.crown_filename, ["tree_volume"])
        # round attribute to 2 decimals

    def attr_enclosingCircle(self, keep_temp: bool):
        """
        Calculates the enclosing circle geometry attributes and adds them to the crown feature class.
        The ratio between Crown Area / Enclosing Cirlce Area identifies elongated polygons.

        -----------------------------------
        EC_diam (MBG_Diameter): the diameter of the enclosing circle (can be used to estimate crown diameter)
        EC_area (Shape_Area): the area of the resulting circle
        ratio_CA_ECA: ratio crown area / enclosing circle area
        outlier_ratio_CA_ECA: classifies the tree crown in normal (0), mild outlier (1) or extreme outlier (2).
            - normal (0) if ratio crown area / enclosing circle area >= 0.25
            - mild outlier (1) if ratio crown area / enclosing circle area < 0.25
            - extreme outlier (2) if ratio crown area / enclosing circle area < 0.02
        -----------------------------------
        """

        self.logger.info("\tATTRIBUTE | EC_diam:")
        self.logger.info(f"\tComputing the enclosing circle diameter... ")
        self.logger.info("\tATTRIBUTE | EC_area:")
        self.logger.info(f"\tComputing the enclosing circle area... ")
        self.logger.info("\tATTRIBUTE | ratio_CA_ECA:")
        self.logger.info(
            f"\tComputing the ratio crown area / enclosing circle area... "
        )
        self.logger.info("\tATTRIBUTE | outlier_ratio_CA_ECA:")
        self.logger.info(
            f"\tClassifying the tree crown as:\n \
                - normal (0) if ratio crown area / enclosing circle area >= 0.25\n \
                - mild outlier (1) if ratio crown area / enclosing circle area < 0.25\n \
                - extreme outlier (2) if ratio crown area / enclosing circle area < 0.02... "
        )

        v_enclosing_circle = os.path.join(self.path, "enclosing_circle_temp")

        # calculate enclosing circle
        arcpy.MinimumBoundingGeometry_management(
            self.crown_filename,
            v_enclosing_circle,
            "CIRCLE",
            "NONE",
            "",
            "MBG_FIELDS",
        )

        # add attribute fields
        field_list = ["EC_diam", "EC_area", "ratio_CA_ECA"]

        for field in field_list:
            au.addField_ifNotExists(self.crown_filename, field, "FLOAT")

        au.addField_ifNotExists(self.crown_filename, "outlier_ratio_CA_ECA", "SHORT")

        # fill attribute fields
        if (
            au.check_isNull(self.crown_filename, "EC_diam") == True
            or au.check_isNull(self.crown_filename, "EC_area") == True
        ):
            # EC_diam and EC_area
            au.join_and_copy(
                t_dest=self.crown_filename,
                join_a_dest="crown_id",
                t_src=v_enclosing_circle,
                join_a_src="crown_id",
                a_src=["MBG_Diameter", "Shape_Area"],
                a_dest=["EC_diam", "EC_area"],
            )

            # calculate ratio crown area / enclosing circle area
            arcpy.CalculateField_management(
                in_table=self.crown_filename,
                field="ratio_CA_ECA",
                expression="!crown_area! / !EC_area!",
                expression_type="PYTHON3",
            )
        else:
            self.logger.info(
                f"\tAll rows in field are already populated. Exiting function."
            )
            # classify tree crown as normal, mild outlier or extreme outlier

        if au.check_isNull(self.crown_filename, "outlier_ratio_CA_ECA") == True:
            with arcpy.da.UpdateCursor(
                self.crown_filename, ["ratio_CA_ECA", "outlier_ratio_CA_ECA"]
            ) as cursor:
                for row in cursor:
                    if row[0] >= 0.25:
                        row[1] = 0
                    elif row[0] < 0.25 and row[0] >= 0.02:
                        row[1] = 1
                    else:
                        row[1] = 2
                    cursor.updateRow(row)

        else:
            self.logger.info(
                f"\tAll rows in field are already populated. Exiting function."
            )

        if keep_temp == False:
            arcpy.Delete_management(v_enclosing_circle)

        au.round_fields_two_decimals(
            self.crown_filename, ["EC_diam", "EC_area", "ratio_CA_ECA"]
        )

    def attr_convexHull(self, keep_temp: bool):
        """
        Calculates the convex hull attributes and adds them to the crown feature class.

        -----------------------------------
        CH_length (MBG_Length): longest distance between any two vertices of the convex hull (crown diameter in this case)
        CH_width (MBG_Width): shortest distance between any two vertices of the convex hull
        CH_area (Shape_Area): convex hull area
        ratio_CA_CHA: ratio crown area / convex hull area
        outlier_ratio_CA_CHA: classifies the tree crown in normal (0), mild outlier (1) or extreme outlier (2).
            - normal (0) if ratio crown area / convex hull area >= 0.7
            - mild outlier (1) if ratio crown area / convex hull area < 0.7
            - extreme outlier (2) if ratio crown area / convex hull area < 0.6
        -----------------------------------
        """

        self.logger.info("\tATTRIBUTE | CH_length:")
        self.logger.info(f"\tComputing the convex hull length... ")
        self.logger.info("\tATTRIBUTE | CH_width:")
        self.logger.info(f"\tComputing the convex hull width... ")
        self.logger.info("\tATTRIBUTE | CH_area:")
        self.logger.info(f"\tComputing the convex hull area... ")
        self.logger.info("\tATTRIBUTE | ratio_CA_CHA:")
        self.logger.info(f"\tComputing the ratio crown area / convex hull area... ")
        self.logger.info("\tATTRIBUTE | outlier_ratio_CA_CHA:")
        self.logger.info(
            f"\tClassifying the tree crown as:\n \
                - normal (0) if ratio crown area / convex hull area >= 0.7\n \
                - mild outlier (1) if ratio crown area / convex hull area < 0.7\n \
                - extreme outlier (2) if ratio crown area / convex hull area < 0.6... "
        )

        v_convex_hull = os.path.join(self.path, "convex_hull_temp")

        field_list = ["CH_length", "CH_width", "CH_area", "ratio_CA_CHA"]

        for field in field_list:
            au.addField_ifNotExists(self.crown_filename, field, "FLOAT")

        au.addField_ifNotExists(self.crown_filename, "outlier_ratio_CA_CHA", "SHORT")

        arcpy.MinimumBoundingGeometry_management(
            self.crown_filename,
            v_convex_hull,
            "CONVEX_HULL",
            "NONE",
            "",
            "MBG_FIELDS",
        )

        # fill attribute fields
        if au.check_isNull(self.crown_filename, field) == True:
            # CH_length, CH_width and CH_area
            au.join_and_copy(
                t_dest=self.crown_filename,
                join_a_dest="crown_id",
                t_src=v_convex_hull,
                join_a_src="crown_id",
                a_src=["MBG_Length", "MBG_Width", "Shape_Area"],
                a_dest=["CH_length", "CH_width", "CH_area"],
            )
            # arcpy.Delete_management(v_convex_hull)

            # calculate ratio crown area / convex hull area
            arcpy.CalculateField_management(
                in_table=self.crown_filename,
                field="ratio_CA_CHA",
                expression="!crown_area! / !CH_area!",
                expression_type="PYTHON3",
            )

            with arcpy.da.UpdateCursor(
                self.crown_filename, ["ratio_CA_CHA", "outlier_ratio_CA_CHA"]
            ) as cursor:
                for row in cursor:
                    if row[0] >= 0.7:
                        row[1] = 0
                    elif row[0] < 0.7 and row[0] >= 0.6:
                        row[1] = 1
                    else:
                        row[1] = 2
                    cursor.updateRow(row)

        else:
            self.logger.info(
                f"\tAll rows in field are already populated. Exiting function."
            )

        if keep_temp == False:
            arcpy.Delete_management(v_convex_hull)

        au.round_fields_two_decimals(
            self.crown_filename,
            ["CH_length", "CH_width", "CH_area", "ratio_CA_CHA"],
        )

    def attr_envelope(self, keep_temp: bool):
        """
        Calculates the envelope attributes and adds them to the crown feature class.

        -----------------------------------
        EV_length (MBG_Length): the lenght of the longer side of the resulting rectangle
        EV_width (MBG_Width): the lenght of the shorter side of the resulting rectangle
        EV_area (Shape_Area): envelope area
        EV_angle (FLOAT): the dominant angle of the envelope, in decimal degrees.
        NS_width: the width of the crown in the north-south direction (0 deg)
        ES_width: the width of the crown in the east-west direction (90 or -90 deg)
        - if angle -90 or 90 degrees, NS_width = envelope length and ES_width = envelope width
        - elif angle 0 or 180 degrees, NS_width = envelope width and ES_width = envelope length
        - else NS_width = None and ES_width = None
        -----------------------------------
        """

        self.logger.info("\tATTRIBUTE | EV_length:")
        self.logger.info(f"\tComputing the envelope length... ")
        self.logger.info("\tATTRIBUTE | EV_width:")
        self.logger.info(f"\tComputing the envelope width... ")
        self.logger.info("\tATTRIBUTE | EV_area:")
        self.logger.info(f"\tComputing the envelope area... ")

        v_envelope = os.path.join(self.path, "envelope_temp")
        arcpy.MinimumBoundingGeometry_management(
            self.crown_filename,
            v_envelope,
            "ENVELOPE",
            "NONE",
            "",
            "MBG_FIELDS",
        )

        field_list_crown = [
            "EV_length",
            "EV_width",
            "EV_area",
            "EV_angle",
            "NS_width",
            "ES_width",
        ]

        for field in field_list_crown:
            au.addField_ifNotExists(self.crown_filename, field, "FLOAT")

        field_list_envelop = ["EV_angle", "NS_width", "ES_width"]
        for field in field_list_envelop:
            au.addField_ifNotExists(v_envelope, field, "FLOAT")

        # fill attribute fields
        if (
            au.check_isNull(self.crown_filename, "EV_length") == True
            or au.check_isNull(self.crown_filename, "EV_width") == True
            or au.check_isNull(self.crown_filename, "EV_area") == True
        ):
            # CH_length, CH_width and CH_area
            au.join_and_copy(
                t_dest=self.crown_filename,
                join_a_dest="crown_id",
                t_src=v_envelope,
                join_a_src="crown_id",
                a_src=["MBG_Length", "MBG_Width", "Shape_Area"],
                a_dest=["EV_length", "EV_width", "EV_area"],
            )
            # arcpy.Delete_management(v_convex_hull)

        else:
            self.logger.info(
                f"\tAll rows in field are already populated. Exiting function."
            )

        # Calculate angle and NS and ES width
        codeblock = """def classify_envAngle(envelope_width, envelope_length, envelope_angle, computed_measure):
                        eps = 1e-2
                        if abs(envelope_angle+90) < eps:
                            if computed_measure == "NS":
                                return envelope_length
                            elif computed_measure == "EW":
                                return envelope_width
                            else:    
                                return None
                        elif abs(envelope_angle) < eps:
                            if computed_measure == "NS":
                                return envelope_width
                            elif computed_measure == "EW":
                                return envelope_length
                            else:    
                                return None
                        else:
                            return None
                    """

        if au.check_isNull(self.crown_filename, "EV_angle") == True:
            arcpy.CalculatePolygonMainAngle_cartography(
                v_envelope, "EV_angle", "GEOGRAPHIC"
            )
            arcpy.CalculateField_management(
                in_table=v_envelope,
                field="NS_width",
                expression="classify_envAngle(!MBG_Width!, !MBG_Length!, !EV_angle!, 'NS')",
                expression_type="PYTHON_9.3",
                code_block=codeblock,
            )
            arcpy.CalculateField_management(
                in_table=v_envelope,
                field="ES_width",
                expression="classify_envAngle(!MBG_Width!, !MBG_Length!, !EV_angle!, 'EW')",
                expression_type="PYTHON_9.3",
                code_block=codeblock,
            )
            # join measures to corresponding crown polygon
            au.join_and_copy(
                t_dest=self.crown_filename,
                join_a_dest="crown_id",
                t_src=v_envelope,
                join_a_src="crown_id",
                a_src=["EV_angle", "NS_width", "ES_width"],
                a_dest=["EV_angle", "NS_width", "ES_width"],
            )

        else:
            self.logger.info(
                f"\tAll rows in field are already populated. Exiting function."
            )

        if keep_temp == False:
            arcpy.Delete_management(v_envelope)

        au.round_fields_two_decimals(
            self.crown_filename,
            [
                "EV_length",
                "EV_width",
                "EV_area",
                "EV_angle",
                "NS_width",
                "ES_width",
            ],
        )

    def attr_crownDiam(self):
        """
        Adds the attribtue 'crown_diam' (FLOAT) to the crown feature class.
            > Computes the crown diameter as maximum length of the convex hull.
        """
        self.logger.info("\tATTRIBUTE | crown_diam:")
        self.logger.info(
            f"\tComputing the crown diameter as maximum length of the convex hull... "
        )
        v_mbg = os.path.join(self.path, "mbg_temp")
        arcpy.MinimumBoundingGeometry_management(
            self.crown_filename,
            v_mbg,
            "CONVEX_HULL",  # tree_detection_v1 uses "CIRCLE"
            "NONE",
            "",
            "MBG_FIELDS",
        )

        in_table = self.crown_filename
        field = "crown_diam"

        self.logger.info(f"\tAdding the attribute <<crown_diam>>... ")
        au.addField_ifNotExists(in_table, field, "FLOAT")

        if au.check_isNull(in_table, field) == True:
            au.join_and_copy(
                t_dest=self.crown_filename,
                join_a_dest="crown_id",
                t_src=v_mbg,
                join_a_src="crown_id",
                a_src=["MBG_Length"],
                a_dest=["crown_diam"],
            )
            arcpy.Delete_management(v_mbg)
        else:
            self.logger.info(
                f"\tAll rows in field are already populated. Exiting function."
            )

        au.round_fields_two_decimals(self.crown_filename, ["crown_diam"])
