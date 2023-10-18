"""Module to clean in situ tree data."""

import logging

import arcpy

from src.utils import arcpy_utils as au


def update_schema_stems(input_field_names, fc, lookup_tb, municipality):
    """Create schema (fields, data, types) for the stems_in_situ feature class

    Args:
        input_field_names (list): field name list of raw in situ tree points
        fc (str): path to interim in situ tree points that needs to be updated
        lookup_tb (df): dataframe with lookup table for attribute fields
        municipality (str): name of municipality
    """
    # set up logger
    logger = logging.getLogger(__name__)

    # clean up fields in stems_in_situ
    # 1. remove all fields except the once in the lookup table
    logger.info(f"Current schema:\n {input_field_names}")
    if input_field_names is not None:
        fields_to_keep = input_field_names
    else:
        fields_to_keep = ["GlobalID", "OBJECTID", "SHAPE", "bydelnummer", "stem_id"]

    fields_to_keep = [field.lower() for field in fields_to_keep]

    fields_to_delete = []
    fields = arcpy.ListFields(fc)
    for field in fields:
        # check lowercase fields to keep
        if field.name.lower() not in fields_to_keep:
            fields_to_delete.append(field.name)

    logger.info(f"Fields to remove:\n {fields_to_delete}")
    if fields_to_delete:
        arcpy.DeleteField_management(fc, fields_to_delete)

    # 2. create data_type lookup dict{field: data_type}

    key = municipality
    value = "data_type"
    data_type_dict = au.df_to_lookupDict(lookup_tb, key, value)
    data_type_dict.pop("GlobalID")  # remove GUIDs
    data_type_dict.pop("FKID_crown")
    print({k: data_type_dict[k] for k in list(data_type_dict)[:5]})

    # 3. create field_name lookup dict{field: new_field_name}
    value = "name"
    field_name_dict = au.df_to_lookupDict(lookup_tb, key, value)

    field_name_dict.pop("GlobalID")
    field_name_dict.pop("FKID_crown")
    print({k: field_name_dict[k] for k in list(field_name_dict)[:5]})

    # 4. create fields with correct data type
    for field, data_type in data_type_dict.items():
        print("Creating field: ", field, " with data type: ", data_type)
        au.addField_ifNotExists(fc, field, str(data_type))

    v_points_fields = arcpy.ListFields(fc)
    v_points_fields = [field.name for field in v_points_fields]

    # 5. rename fields
    for field, new_field_name in field_name_dict.items():
        if field in v_points_fields:
            print("Renaming field: ", field, " to: ", new_field_name)
            arcpy.AlterField_management(
                in_table=fc,
                field=field,
                new_field_name=new_field_name,
                new_field_alias=new_field_name,
            )

    updated_field_list = arcpy.ListFields(fc)
    schema = [field.name for field in updated_field_list]
    logger.info(f"Updated schema:\n {schema}")
    logger.info("Reorder the attribute fields manually. ")

    # TODO reorder fields using lookup_tb order in code instead of maually
    return
