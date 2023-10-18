import logging
import os

import arcpy
import pandas as pd
from arcpy import env

from src import DATA_PATH, INTERIM_PATH, MUNICIPALITY
from src import arcpy_utils as au
from src import logger

# ------------------------------------------------------ #
# FLOAT: up to 6 decimal places
# DOUBLE: up to 15 decimal places
# LONG: up to 10 digits
# SHORT: up to 5 digits
# GUID: 38 characters
# TEXT: 255 characters
# ------------------------------------------------------ #


class InsituAttributes:
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

    def __init__(self, gdb_path: str, fc_filename: str):
        self.gdb_path = gdb_path
        self.fc_filename = fc_filename

    def attr_species(self, excel_path: str, sheet_name: str, norwegian_name_field: str):
        """classifies the tree species based on a lookup table

        Args:
            excel_path (_type_): path to ecel lookup fiel
            sheet_name (_type_): lookup sheet
            norwegian_name_field (_type_): field with the "original norwegian name"
            (norsk_navn, treslag osv..)
        """

        # print feature calss field names list

        env.workspace = self.gdb_path

        # for field in arcpy.ListFields(self.fc_filename):
        # print(field.name)

        arcpy.AlterField_management(
            in_table=self.fc_filename,
            field=norwegian_name_field,
            new_field_name="norwegian_name",
            new_field_alias="norwegian_name",
        )

        # add species field if not exists
        field_type = "TEXT"
        fieldName = [
            "itree_species_code",
            "scientific_name",
            "taxon_genus",
            "common_name",
            "norwegian_name",
            "species_origin",
        ]
        for field in fieldName:
            au.addField_ifNotExists(self.fc_filename, field, field_type)

        # import lookup table
        df = pd.read_excel(excel_path, sheet_name=sheet_name)
        print(df.head())

        # lookup value based on "norwegian_name"
        key = "norwegian_name"
        values = ["itree_species_code", "scientific_name", "taxon_genus", "common_name"]

        for v in values:
            lookup_dict = au.df_to_lookupDict(df, key, v)
            field_to_check = key
            field_to_modify = v

            au.reclassify_row(
                self.fc_filename, field_to_check, field_to_modify, lookup_dict
            )

        # CALCULATE SPECIES_ORIGIN
        # feltregistering
        codeblock = """def calcSpeciesOrigin(norwegian_name, species_origin):
            if norwegian_name != None:
                return "feltregistrering"
            if species_origin != None:
                return species_origin
            else: 
                return None
            """

        arcpy.CalculateField_management(
            in_table=self.fc_filename,
            field="species_origin",
            expression="calcSpeciesOrigin(!norwegian_name!, !species_origin!)",
            expression_type="PYTHON9.3",
            code_block=codeblock,
        )

        logger.info(
            "You might need to reload ArcGIS Pro to see the changes in the attribute table."
        )

        return

    def attr_dbh(self):
        """calculates dbh, dbh_height and dbh_origin"""
        # add dbh fields if not exists
        field_type = "FLOAT"
        fieldName = ["dbh", "dbh_height"]
        for field in fieldName:
            au.addField_ifNotExists(self.fc_filename, field, field_type)

        au.addField_ifNotExists(self.fc_filename, "dbh_origin", "TEXT")

        # ------------------------------------------------------ #
        # DBH
        # TODO ONLY calculate with import
        # ------------------------------------------------------ #

        # CALCULATE DBH_ORIGIN
        # CASE 3: feltregistrering
        # CASE 1,2,4: dbh = 4.04 * height^0.82 (based on oslo data)
        # CASE 1,2, 4: dbh = (crown_diam^2.63)/(3.48^2.63) (based on oslo data)
        codeblock = """def calcDBH_origin(stem_circumference,dbh, height_total_tree, crown_diam):
            if stem_circumference != None:
                return "feltregistrering"
            elif height_total_tree != None:
                return "dbh = 4.04 * height^0.82"
            elif crown_diam != None:
                return "dbh = (crown_diam^2.63)/(3.48^2.63)"
            else:
                return None
            """

        arcpy.CalculateField_management(
            in_table=self.fc_filename,
            field="dbh_origin",
            expression="calcDBH_origin(!stem_circumference!, !dbh!, !height_total_tree!, !crown_diam!)",
            expression_type="PYTHON9.3",
            code_block=codeblock,
        )

        # CALCULATE DBH
        # CASE 3: dbh = circumference / pi
        # CASE 1,2,4: dbh = 4.04 * height^0.82 (based on oslo data)
        # CASE 1,2,4: dbh = (crown_diam^2.63)/(3.48^2.63) (based on oslo data)
        codeblock = """def calcDBH(stem_circumference, dbh, height_total_tree, crown_diam):
            if stem_circumference != None:
                return stem_circumference/3.14159265359
            elif height_total_tree != None:
                return 4.04*(height_total_tree**0.82)
            elif crown_diam != None:
                return (crown_diam**2.63)/(3.48**2.63)
            else:
                return None
        """

        arcpy.CalculateField_management(
            in_table=self.fc_filename,
            field="dbh",
            expression="calcDBH(!stem_circumference!, !dbh!, !height_total_tree!, !crown_diam!)",
            expression_type="PYTHON9.3",
            code_block=codeblock,
        )

        # CALCULATE DBH_HEIGHT
        # set dbh_height (meauserment height of dbh) to 1.37
        codeblock = """def calcDBH_height(stem_circumference, dbh):
            if dbh != None:
                return 1.37
            elif stem_circumference != None:
                return 1.37
            else:
                return None
        """

        arcpy.CalculateField_management(
            in_table=self.fc_filename,
            field="dbh_height",
            expression="calcDBH_height(!stem_circumference!, !dbh!)",
            expression_type="PYTHON9.3",
            code_block=codeblock,
        )


if __name__ == "__main__":
    # Recalssify the columns taxon_genus, taxon_type and common_name:
    gdb_path = os.path.join(INTERIM_PATH, "itree_attributes.gdb")
    au.createGDB_ifNotExists(gdb_path)

    fc_filename = os.path.join(gdb_path, "points_in_situ")

    excel_path = os.path.join(DATA_PATH, "lookup_tables", "lookup_tree_species.xlsx")
    print(excel_path)

    insitu = InsituAttributes(gdb_path, fc_filename)

    # change "norwegian_name_field" to municipality specific field name
    # Bodo = "Treslag"
    insitu.lookup_tree_species(
        excel_path=excel_path,
        sheet_name="itree_species_lookup",
        norwegian_name_field="norwegian_name",
    )
