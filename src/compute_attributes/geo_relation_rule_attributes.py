import logging

import arcpy

from src.utils import arcpy_utils as au

# ------------------------------------------------------ #
# FLOAT: up to 6 decimal places
# DOUBLE: up to 15 decimal places
# LONG: up to 10 digits
# SHORT: up to 5 digits
# GUID: 38 characters
# TEXT: 255 characters
# ------------------------------------------------------ #


class RuleAttributes:
    """
    A class for computing tree attributes.

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

    """

    def __init__(self, gdb_path: str, fc_filename: str, logger=None):
        self.gdb_path = gdb_path
        self.fc_filename = fc_filename
        self.logger = logger or logging.getLogger(__name__)

    def attr_ruleHeight(self):
        """Import values from raw in situ data to the stems_in_situ feature class"""
        # ------------------------------------------------------ #
        # CALCULATE HEIGHT
        # TODO calculate after geo_relation
        # ------------------------------------------------------ #

        # CALCULATE HEIGHT_ORIGIN
        # CASE 1, 2, 4: laserdata
        # CASE 3: feltregistering
        # CASE 3: height_total_tree = (dbh*1.22)/(4.04**1.22)"
        au.addField_ifNotExists(self.fc_filename, "height_origin", "TEXT")

        codeblock = """def calcHeight_origin(geo_relation, tree_height_laser, height_insitu, dbh):
            if tree_height_laser != None:
                return "laserdata"
            if geo_relation == "Case 3":
                if height_insitu != None:
                    return "feltregistering"
                elif dbh != None:
                    return "height_total_tree = (dbh*1.22)/(4.04**1.22)"
                else:
                    return "tree height not available"
            else:
                return None
        """

        arcpy.CalculateField_management(
            in_table=self.fc_filename,
            field="height_origin",
            expression="calcHeight_origin(!geo_relation!, !tree_height_laser!,!height_insitu!, !dbh!)",
            expression_type="PYTHON9.3",
            code_block=codeblock,
        )

        au.addField_ifNotExists(self.fc_filename, "height_total_tree", "FLOAT")
        # calculate height_total_tree
        # CASE 1, 2, 4: laserdata
        # CASE 3: feltregistering
        # CASE 3: (dbh*1.22)/(4.04**1.22)"
        codeblock = """def calcHeight(geo_relation, tree_height_laser, height_insitu, dbh):
            if tree_height_laser != None:
                return tree_height_laser
            if geo_relation == "Case 3":
                if height_insitu != None:
                    return height_insitu
                elif dbh != None:
                    return (dbh*1.22)/(4.04**1.22)
            else:
                return None
        """

        arcpy.CalculateField_management(
            in_table=self.fc_filename,
            field="height_total_tree",
            expression="calcHeight(!geo_relation!, !tree_height_laser!, !height_insitu!, !dbh!)",
            expression_type="PYTHON9.3",
            code_block=codeblock,
        )

    def attr_ruleCrown(self):
        # ------------------------------------------------------ #
        # CROWN
        # TODO calculate after geo_relation
        # ------------------------------------------------------ #

        au.addField_ifNotExists(self.fc_filename, "crown_origin", "TEXT")
        # calculate crown_origin
        # CASE 1, 2, 4: laserdata
        # CASE 3: feltregistrering
        # CASE 3: crown_diam = 3.48*(dbh**0.38)
        codeblock = """def calcCrown_origin(geo_relation, crown_diam, crown_diam_insitu, dbh, crown_origin):
            if geo_relation != 'Case 3' and geo_relation != None:
                return "laserdata"
            if geo_relation == 'Case 3':
                if crown_diam_insitu != None:
                    return "feltregistrering"
                if dbh != None:
                    return "crown_diam = 3.48*(dbh**0.38)"
                else: 
                    return "crown geometry not available"
            else:
                return None
        """

        arcpy.CalculateField_management(
            in_table=self.fc_filename,
            field="crown_origin",
            expression="calcCrown_origin(!geo_relation!, !crown_diam!, !crown_diam_insitu!, !dbh!, !crown_origin!)",
            expression_type="PYTHON9.3",
            code_block=codeblock,
        )

        # calculate crown_diam
        # CASE 1, 2, 4: laserdata
        # CASE 3: insitu
        # CASE 3: dbh = 3.48*(dbh**0.38)

        au.addField_ifNotExists(self.fc_filename, "crown_diam", "FLOAT")
        codeblock = """def calcCrown_diam(geo_relation, crown_diam, crown_diam_insitu, dbh):
            if geo_relation != 'Case 3' and geo_relation != None:
                return crown_diam
            if geo_relation == "Case 3":
                if crown_diam_insitu != None:
                    return crown_diam_insitu
                if dbh != None:
                    return 3.48*(dbh**0.38)
            else:
                return None
            """

        arcpy.CalculateField_management(
            in_table=self.fc_filename,
            field="crown_diam",
            expression="calcCrown_diam(!geo_relation!, !crown_diam!, !crown_diam_insitu!, !dbh!)",
            expression_type="PYTHON9.3",
            code_block=codeblock,
        )

        # calculate crown_radius
        # CASE 1, 2, 4: do not calculate crown_radius!
        # CASE 3: crown_radius_insitu = crown_diam_insitu/2
        # CASE 3: crown_radius = (3.48*(dbh**0.38))/2
        au.addField_ifNotExists(self.fc_filename, "crown_radius", "FLOAT")

        codeblock = """def calcCrown_radius(crown_diam, crown_diam_insitu, dbh, crown_radius):
            if crown_diam != None:
                return crown_diam/2
            if crown_diam_insitu != None:
                return crown_diam_insitu/2
            if dbh != None:
                return (3.48*(dbh**0.38))/2
            else:
                return None
        """

        arcpy.CalculateField_management(
            in_table=self.fc_filename,
            field="crown_radius",
            expression="calcCrown_radius(!crown_diam!, !crown_diam_insitu!, !dbh!, !crown_radius!)",
            expression_type="PYTHON9.3",
            code_block=codeblock,
        )
