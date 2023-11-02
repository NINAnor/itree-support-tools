import arcpy
import logging
import os
import pandas as pd

from src.utils import arcpy_utils as au
from src.config.config import load_catalog, load_parameters
from src.config.logger import setup_logging
from src.data import load


def remove_fields(fc, fields_to_keep=None):
    """Remove fields from feature class

    Args:
        fc (str): path to feature class
        fields_to_keep (list): list of fields to keep

    Returns:
        fc (str): path to feature class with updated fields
    """

    # set up logger
    logger = logging.getLogger(__name__)

    if fields_to_keep is not None:
        fields_to_keep = fields_to_keep
        # fields_to_keep = ["GlobalID", "OBJECTID", "SHAPE"]
    else:
        logger.info("No fields to keep specified. Keeping all fields")
        return

    fields_to_keep = [field.lower() for field in fields_to_keep]

    fields_to_delete = []
    fields = arcpy.ListFields(fc)
    for field in fields:
        if field.name.lower() not in fields_to_keep:
            fields_to_delete.append(field.name)

    for x in ["GlobalID", "OBJECTID", "Shape", "Shape_Area", "Shape_Length"]:
        # remove ["GlobalID", "OBJECTID", "SHAPE"] from list
        if x in fields_to_delete:
            fields_to_delete.remove(x)

    logger.info(f"Fields to remove:\n {fields_to_delete}")

    if fields_to_delete:
        arcpy.DeleteField_management(fc, fields_to_delete)

    return fc


def alter_fields_from_lookup(
    fc, df_lookup, name_col="name", data_type_col="data_type", alias_col="alias"
):
    """
    Alter fields from lookup table

    Args:
        fc (str): path to feature class
        df_lookup (pd.DataFrame): lookup table
        name_col (str): column name with field names
        data_type_col (str): column name with data types
        alias_col (str): column name with alias names

    Returns:
        fc (str): path to feature class with updated fields
    """

    # set up logger
    logger = logging.getLogger(__name__)

    #  create data_type lookup dict{name:data_type}
    data_type_dict = au.df_to_lookupDict(df_lookup, name_col, data_type_col)
    logger.info("Data type dict [:5]:")
    logger.info({k: data_type_dict[k] for k in list(data_type_dict)[:5]})

    # create alias lookup dict{name:alias}
    field_name_dict = au.df_to_lookupDict(df_lookup, name_col, alias_col)
    logger.info("Field name dict [:5]:")
    logger.info({k: field_name_dict[k] for k in list(field_name_dict)[:5]})

    # create fields with correct data type and alias name
    for field, data_type in data_type_dict.items():
        # Do not alter ID and geom fields
        if field not in ["GlobalID", "OBJECTID", "Shape", "Shape_Area", "Shape_Length"]:
            # print("Creating field: ", field, " with data type: ", data_type)
            au.addField_ifNotExists(fc, field, str(data_type))

    field_names = arcpy.ListFields(fc)
    field_list = [field.name for field in field_names]

    # rename field alias name
    for field, alias in field_name_dict.items():
        if field in field_list:
            # print("Renaming field (alias): ", field, "---", alias)
            arcpy.AlterField_management(
                in_table=fc,
                field=field,
                new_field_name=field,
                new_field_alias=alias,
            )

    new_field_names = arcpy.ListFields(fc)
    new_field_list = [field.name for field in new_field_names]
    logger.info(f"Altered fields:\n {new_field_list}")

    return fc


if __name__ == "__main__":
    # set up logger
    setup_logging()
    logger = logging.getLogger(__name__)

    # load catalog and params
    logger.info("Loading catalog...")
    catalog = load_catalog()
    logger.info("Loading parameters...")
    parameters = load_parameters()

    # set municipality
    municipality = parameters["municipality"]

    # --- load data ---
    gdb_tree_db = catalog["tree_db"]["filepath"]

    # create dict
    # fc: (itree_resultater, registrerte_traer, registrerte_trekroner, trekroner)
    # lookup: (itree_resultater_fields, traer_fields, itree_trekroner_fields, trekroner_fields)

    dic_lookup = {}
    dic_ftk = {}
    for i, j in zip((0, 1, 2, 3, 4), (2, 6, 3, 7, 7)):
        fc = catalog["tree_db"]["fc"][i]
        fc_path = os.path.join(gdb_tree_db, fc)

        df = load.lookup_table(
            excel_path=catalog["lookup_fields"]["filepath"],
            sheet_name=catalog["lookup_fields"]["sheet_names"][j],
        )

        # append to dic
        dic_lookup[fc_path] = df
        dic_ftk[fc_path] = df["name"].tolist()

    # print(dic_lookup)
    # print(dic_ftk)

    # alter fields
    for key, value in dic_lookup.items():
        alter_fields_from_lookup(key, value)

    for key, value in dic_ftk.items():
        remove_fields(key, fields_to_keep=value)
