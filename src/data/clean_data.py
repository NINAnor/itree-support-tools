import logging

import arcpy

from src.utils import arcpy_utils as au


def create_schema(v_points, df_lookup, municipality, raw_insitu_fields):
    """Create schema (fields, data, types) for the stems_in_situ feature class

    Args:
        v_points (_type_): path to stems_in_situ feature class
        excel_path: lookup table for field names and data types
    """
    # set up logger
    logger = logging.getLogger(__name__)

    if raw_insitu_fields is not None:
        fields_to_keep = raw_insitu_fields
    else:
        fields_to_keep = ["GlobalID", "OBJECTID", "SHAPE", "bydelnummer", "stem_id"]

    # lowercase
    fields_to_keep = [field.lower() for field in fields_to_keep]

    # loop through fields and delete all fields except the once in fields_to_keep
    fields_to_delete = []
    fields = arcpy.ListFields(v_points)
    for field in fields:
        # check lowercase fields to keep
        if field.name.lower() not in fields_to_keep:
            fields_to_delete.append(field.name)

    if fields_to_delete:
        arcpy.DeleteField_management(v_points, fields_to_delete)

    logger.info("Fields removed:\n ", fields_to_delete)

    # get dict with field_name, date_type
    key = municipality
    value = "data_type"
    fieldmapping_dict = au.df_to_lookupDict(df_lookup, key, value)
    fieldmapping_dict.pop("GlobalID")  # remove GUIDs
    fieldmapping_dict.pop("FKID_crown")
    print({k: fieldmapping_dict[k] for k in list(fieldmapping_dict)[:5]})

    return
    key = municipality
    value = "name"
    field_rename_dict = au.df_to_lookupDict(df, key, value)

    field_rename_dict.pop("GlobalID")
    field_rename_dict.pop("FKID_crown")
    print({k: field_rename_dict[k] for k in list(field_rename_dict)[:5]})

    # loop through fieldmapping dict and create fields
    for field, data_type in fieldmapping_dict.items():
        print("Creating field: ", field, " with data type: ", data_type)
        au.addField_ifNotExists(v_points, field, str(data_type))

    v_points_fields = arcpy.ListFields(v_points)
    v_points_fields = [field.name for field in v_points_fields]
    # loop through field_rename_dict and rename fields
    for field, new_field_name in field_rename_dict.items():
        if field in v_points_fields:
            print("Renaming field: ", field, " to: ", new_field_name)
            arcpy.AlterField_management(
                in_table=v_points,
                field=field,
                new_field_name=new_field_name,
                new_field_alias=new_field_name,
            )

    updated_field_list = arcpy.ListFields(v_points)
    schema = [field.name for field in updated_field_list]
    print("Updated schema:\n", schema)
    print("Reorder fields manually. ")
    # TODO reorder fields to the same order as given in the lookup table
    # either using pandas or fieldmappings in arcpy
