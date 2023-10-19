"""Module to clean in situ tree data."""

import logging

import arcpy

from src.attributes.admin_attributes import AdminAttributes
from src.attributes.geo_relation_rule_attributes import RuleAttributes
from src.attributes.insitu_attributes import InsituAttributes
from src.utils import arcpy_utils as au


def update_schema_stems(input_field_list, input_fc, lookup_df, municipality):
    """Create schema (fields, data, types) for the stems_in_situ feature class

    Args:
        input_field_names (list): field name list of raw in situ tree points
        input_fc (str): path to interim in situ tree points that needs to be updated
        lookup_df (df): dataframe with lookup table for attribute fields
        municipality (str): name of municipality
    """
    # set up logger
    logger = logging.getLogger(__name__)

    # clean up fields in stems_in_situ
    # 1. remove all fields except the once in the lookup table
    logger.info(f"Current schema:\n {input_field_list}")
    if input_field_list is not None:
        fields_to_keep = input_field_list
    else:
        fields_to_keep = ["GlobalID", "OBJECTID", "SHAPE", "bydelnummer", "stem_id"]

    fields_to_keep = [field.lower() for field in fields_to_keep]

    fields_to_delete = []
    fields = arcpy.ListFields(input_fc)
    for field in fields:
        # check lowercase fields to keep
        if field.name.lower() not in fields_to_keep:
            fields_to_delete.append(field.name)

    logger.info(f"Fields to remove:\n {fields_to_delete}")
    if fields_to_delete:
        arcpy.DeleteField_management(input_fc, fields_to_delete)

    # 2. create data_type lookup dict{field: data_type}

    key = municipality
    value = "data_type"
    data_type_dict = au.df_to_lookupDict(lookup_df, key, value)
    data_type_dict.pop("GlobalID")  # remove GUIDs
    data_type_dict.pop("FKID_crown")
    print({k: data_type_dict[k] for k in list(data_type_dict)[:5]})

    # 3. create field_name lookup dict{field: new_field_name}
    value = "name"
    field_name_dict = au.df_to_lookupDict(lookup_df, key, value)

    field_name_dict.pop("GlobalID")
    field_name_dict.pop("FKID_crown")
    print({k: field_name_dict[k] for k in list(field_name_dict)[:5]})

    # 4. create fields with correct data type
    for field, data_type in data_type_dict.items():
        print("Creating field: ", field, " with data type: ", data_type)
        au.addField_ifNotExists(input_fc, field, str(data_type))

    v_points_fields = arcpy.ListFields(input_fc)
    v_points_fields = [field.name for field in v_points_fields]

    # 5. rename fields
    for field, new_field_name in field_name_dict.items():
        if field in v_points_fields:
            print("Renaming field: ", field, " to: ", new_field_name)
            arcpy.AlterField_management(
                in_table=input_fc,
                field=field,
                new_field_name=new_field_name,
                new_field_alias=new_field_name,
            )

    updated_field_list = arcpy.ListFields(input_fc)
    schema = [field.name for field in updated_field_list]
    logger.info(f"Updated schema:\n {schema}")
    logger.info("Reorder the attribute fields manually. ")

    # TODO reorder fields using lookup_df order in code instead of maually
    return


def fill_attributes(input_gdb, input_fc, lookup_excel, lookup_sheet):
    InsituAttribute = InsituAttributes(input_gdb, input_fc)
    InsituAttribute.attr_species(
        excel_path=lookup_excel,
        sheet_name=lookup_sheet,
        norwegian_name_field="norwegian_name",
    )

    InsituAttribute.attr_dbh()

    AdminAttribute = AdminAttributes(input_gdb, input_fc, input_fc)
    AdminAttribute.attr_treeID()

    rule_attr = RuleAttributes(input_gdb, input_fc)
    rule_attr.attr_ruleHeight()
    rule_attr.attr_ruleCrown()


def clean_points(input_fc):
    """Clean input points for the geo_relation classificaiton

    Args:
        input_fc (_type_): _description_
    """

    fields_to_keep = [
        "GlobalID",
        "OBJECTID",
        "SHAPE",
        "bydelnummer",
        "stem_id",
        "geo_relation",
        "dbh",
        "height_total_tree",
        "tree_height_laser",
        "height_insitu",
        "height_origin",
        "crown_radius",
        "crown_diam",
        "crown_diam_insitu",
        "crown_origin",
    ]
    fields = arcpy.ListFields(input_fc)

    fields_to_keep = [field.lower() for field in fields_to_keep]

    # delete all fields except the following
    fields_to_delete = []
    for field in fields:
        if field.name.lower() not in fields_to_keep:
            fields_to_delete.append(field.name)

    arcpy.DeleteField_management(input_fc, fields_to_delete)

    print("Fields removed: ", fields_to_delete)


def group_by_neighbourhood(point_fc, polygon_fc, selecting_key, output_gdb, output_key):
    logger = logging.getLogger(__name__)
    # group stems per neighbourhood
    dict_points = au.exportPoints_byPolygon(
        point_layer=point_fc,
        polygon_layer=polygon_fc,
        selecting_field=selecting_key,
        output_gdb=output_gdb,
        output_id_field=output_key,
    )

    # iterate over dictionary with point files per neighbourhood and clean up the data
    for key, value in dict_points.items():
        logger.info(f"Cleaning up {key}...")
        clean_points(value)
        rule_attributes = RuleAttributes(output_gdb, value)
        rule_attributes.attr_ruleHeight()
        rule_attributes.attr_ruleCrown()
