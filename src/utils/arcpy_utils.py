"""util functions for working with arcpy."""
import logging
import os

import arcpy
from arcpy.ia import *
from arcpy.sa import *

# from logger import setup_logger


# --------------------------------------------------------------------------- #
# LOOKUP AND RECLASSIY/RENAME FUNCTIONS
# --------------------------------------------------------------------------- #


def df_to_lookupDict(df, key, value):
    # strip whitespace from key and value columns
    lookup_dict = {}
    for index, row in df.iterrows():
        lookup_dict[row[key].strip()] = row[value].strip()
    return lookup_dict


def reclassify_row(fc, field_to_check, field_to_modify, lookup_dict):
    """Reclassifies values in a specified field based on a lookup table.

    Args:
        fc (str): The path to the feature class.
        field_to_check (str): The name of the field to check against the lookup table.
        field_to_modify (str): The name of the field to modify based on the lookup table.
        lookup_dict (dict): A dictionary object containing lookup values as keys and their corresponding new values as values.
    """

    # init logger
    logger = logging.getLogger(__name__)

    # Create a case-insensitive dictionary for the lookup values
    lookup_dict_case_insensitive = {k.lower(): v for k, v in lookup_dict.items()}

    # Create an update cursor to modify the values in the field
    fields = [field_to_check, field_to_modify]
    # sql_clause = f"{field_to_check} IS NOT NULL"
    with arcpy.da.UpdateCursor(fc, fields) as cursor:
        for row in cursor:
            lookup_value = lookup_dict_case_insensitive.get(str(row[0]).lower())
            if lookup_value is not None:
                row[1] = lookup_value

            # Update the cursor (make sure it is outside of the if statement!)
            cursor.updateRow(row)
            # print(f"Reclassified value <{row[0]}> to value <{lookup_value}>")

    # Print a message indicating the update is complete
    print(f"The rows in <{field_to_modify}> are reclassified.")


# --------------------------------------------------------------------------- #
# JOIN/MERGE/EXTRACT FUNCTIONS
# --------------------------------------------------------------------------- #


def join_and_copy(
    t_dest: str,
    join_a_dest: str,
    t_src: str,
    join_a_src: str,
    a_src: list,
    a_dest: list,
):
    """
    Join "source_table" to "destination table" and copy attributes from "source table"
    to attributes in "destination table".

    Args:
        t_dest (str): destinatation table, table view to wich the join will be added.
        join_a_dest (str): destination field, the field in the dst table on which the join will be based.
        t_src (str): source table (join table), the table view to be joined to the destination table.
        join_a_src (str): source field (join field), the field in the source table on which the join will be based.
        a_src (list): source list of fields (join field list), the list of fields to be copied from the source table to the destination table.
        a_dest (str): destination list of fields, the name of the source fields to where the copied values will be stored in the destination table.
    """
    # init logger
    logger = logging.getLogger(__name__)

    name_dest = arcpy.Describe(t_dest).name
    name_src = arcpy.Describe(t_src).name

    # Create layer from "destination table"
    l_dest = "dest_lyr"
    arcpy.MakeFeatureLayer_management(t_dest, l_dest)

    # Join
    arcpy.AddJoin_management(l_dest, join_a_dest, t_src, join_a_src)

    # Copy attributes
    for src_field, dest_field in zip(a_src, a_dest):
        logger.info(
            "\tCopying values from "
            + name_src
            + "."
            + src_field
            + " to "
            + name_dest
            + "."
            + dest_field
        )
        arcpy.CalculateField_management(
            l_dest, name_dest + "." + dest_field, "!" + name_src + "." + src_field + "!"
        )

    # remove layer!
    arcpy.Delete_management(l_dest)


def extractFeatures_byID(
    target_feature: str, id_feature: str, output_feature: str, id_field: str
):
    """
    This function extracts features from a feature lyr based on a list
    of unique IDs derived from another feature lyr.

    Args:
        target_feature (str): Target feature layer path
        id_feature (str): Path to the layer that contains the selecting ids
        output_feature (str): Output feature layer path
    """
    # init logger
    logger = logging.getLogger(__name__)

    # Get unique IDs from the id_feature layer
    ids = set(row[0] for row in arcpy.da.SearchCursor(id_feature, id_field))
    sorted_ids = sorted(list(ids))
    print("number of ids:", len(sorted_ids))

    # Select the features in the target layer if the ID is in the ID_list
    where_clause = f"{id_field} IN ({','.join(map(str, sorted_ids))})"
    selected_layer = arcpy.management.MakeFeatureLayer(
        target_feature, "selected_layer", where_clause
    )

    # Copy the selected features to the output feature layer
    arcpy.management.CopyFeatures(selected_layer, output_feature)


# --------------------------------------------------------------------------- #
# ifNotExists or ifEmpty FUNCTIONS
# --------------------------------------------------------------------------- #


def createGDB_ifNotExists(filegdb_path: str):
    """
    Checks if a fileGDB exists and if not creates this fileGDB

    Args:
        filegdb_path (str): path to the fileGDB
    """
    # init logger
    logger = logging.getLogger(__name__)

    filegdb_name = os.path.basename(filegdb_path)
    if arcpy.Exists(filegdb_path):
        logger.info("\tFileGDB {} already exists. Continue...".format(filegdb_name))
    else:
        dir_path = os.path.dirname(filegdb_path)
        arcpy.management.CreateFileGDB(dir_path, filegdb_name)


def createDataset_ifNotExists(gdb_path: str, dataset_name: str, coord_system: str):
    """_summary_

    Args:
        gdb_path (str): _description_
        dataset_name (str): _description_
        spatial_reference (str): _description_
    """
    # init logger
    logger = logging.getLogger(__name__)

    if arcpy.Exists(os.path.join(gdb_path, dataset_name)):
        logger.info(f"\tDataset {dataset_name} already exists. Continue...")
    else:
        logger.info(f"\tCreating dataset {dataset_name}...")
        # create dataset in filegdb
        arcpy.CreateFeatureDataset_management(
            out_dataset_path=gdb_path,
            out_name=dataset_name,
            spatial_reference=coord_system,
        )


def copyFeature_ifNotExists(in_fc: str, out_fc: str):
    """
    Checks if a feature exists in a file GDB and if not copies this feature

    Args:
        in_fc (str): path to the input feature (that will be copied.)
        out_fc (str): path to the output feature
    """
    # init logger
    logger = logging.getLogger(__name__)

    if arcpy.Exists(out_fc):
        logger.info(f"\tFeature {os.path.basename(out_fc)} already exists. Continue...")
    else:
        arcpy.management.CopyFeatures(in_fc, out_fc)


def fieldExist(featureclass: str, fieldname: str):
    """
    Check if an attribute field exists

    Args:
        featureclass (str): The path to the feature class.
        fieldname (str): The name of the field to check.

    Returns:
        bool: True if the field exists, False otherwise.
    """

    fieldList = arcpy.ListFields(featureclass, fieldname)
    fieldCount = len(fieldList)

    if fieldCount == 1:
        return True
    else:
        return False


def addField_ifNotExists(featureclass: str, fieldname: str, type: str):
    """
    Adds a field to a feature class if the field does not already exist.

    Args:
        featureclass (str): The path to the feature class.
        fieldname (str): The name of the field to add.
        type (str): The data type of the field to add.
    """
    if not fieldExist(featureclass, fieldname):
        arcpy.AddField_management(featureclass, fieldname, type)


def calculateField_ifEmpty(in_table: str, field: str, expression: str, code_block=""):
    """
    Check if a field in a table contains any null or empty values. If so, recalculate the field using the provided
    expression and code block.

    Args:
        in_table (str): The input table.
        field (str): The field to check and calculate.
        expression (str): The expression to use for the calculation.
        code_block (str, optional): The code block to use for the calculation. Defaults to "".
    """

    # init logger
    logger = logging.getLogger(__name__)

    # Check if column contains any null or empty values
    with arcpy.da.SearchCursor(in_table, [field]) as cursor:
        has_nulls = False
        for row in cursor:
            if row[0] is None or row[0] == "":
                has_nulls = True
                break

    # If the column contains null or empty values, recalculate it
    if has_nulls:
        arcpy.management.CalculateField(
            in_table=in_table,
            field=field,
            expression=expression,
            expression_type="PYTHON_9.3",
            code_block=code_block,
        )
        logger.info(f"\tThe Column <{field}> has filled with values. Continue...")
    else:
        logger.info(f"\tThe Column <{field}> does not contain null or empty values.")


def check_isNull(in_table: str, field: str, type: str) -> bool:
    """
    Checks if a specified field in a feature class contains any null or empty values.

    Args:
    fc (str): The path to the feature class to check.
    field (str): The name of the field to check for null or empty values.

    Returns:
    True if there are null or empty values in the field, False otherwise.
    """
    # init logger
    logger = logging.getLogger(__name__)

    # Check if column exists
    addField_ifNotExists(in_table, field, type)

    with arcpy.da.SearchCursor(in_table, [field]) as cursor:
        null_count = 0
        for row in cursor:
            if row[0] is None:
                null_count += 1
            if row[0] == "":
                null_count += 1
            if row[0] == "null values":
                null_count += 1

        logger.info(f"\tThe count of Null values in {field} is: {null_count}")
        if null_count == 0:
            logger.info("\tThe field is already populated. Continue..")
            return False
        else:
            logger.info("\tThe field contains null values. Recalculate...")
            return True


def deleteFields(in_table, out_table, keep_list):
    """Deletes all fields from a table except required fields
    and those in the keep_list.

    Args:
        in_table (str): path to the input table
        keep_list (str): list of fields to keep
    """
    # init logger
    logger = logging.getLogger(__name__)

    # Describe the input (need to test the dataset and data types)
    desc = arcpy.Describe(in_table)

    # Make a copy of the input (so you can maintain the original as is)
    if desc.datasetType == "FeatureClass":
        arcpy.CopyFeatures_management(in_table, out_table)
    else:
        arcpy.CopyRows_management(in_table, out_table)

    fieldObj_list = arcpy.ListFields(out_table)

    # Create an empty list that will be populated with field names
    field_list = []

    for field in fieldObj_list:
        if not field.required and field.name not in keep_list:
            field_list.append(field.name)

    # dBASE tables require a field other than an OID and Shape. If this is
    # the case, retain an extra field (the first one in the original list
    if desc.dataType in ["ShapeFile", "DbaseTable"]:
        field_list = field_list[1:]

    print(f"Keep the fields: {keep_list}.")
    print(f"Delete the fields: {field_list}.")
    arcpy.DeleteField_management(out_table, field_list)


def deleteDuplicates(table, field):
    """
    Delete duplicate records from a table based on a specified field.

    Args:
        table (str): path to the input table
        field (str): field name to check for duplicates
    """
    # init logger
    logger = logging.getLogger(__name__)

    # Create a list to store the unique tree IDs
    unique_tree_ids = []

    # Create a search cursor to iterate over the table
    with arcpy.da.SearchCursor(table, field) as cursor:
        for row in cursor:
            tree_id = row[0]
            # Check if the tree ID is already in the unique_tree_ids list
            if tree_id not in unique_tree_ids:
                unique_tree_ids.append(tree_id)

    # Use DeleteIdentical_management to delete duplicates based on tree_id
    arcpy.DeleteIdentical_management(table, field)

    # Print the unique tree IDs that remain in the table
    # print(f"Unique Tree IDs: {len(unique_tree_ids)}")


# --------------------------------------------------------------------------- #
# Raster functions
# --------------------------------------------------------------------------- #


def convert_toIntRaster(float_raster, int_raster):
    """Converst a float to an integer raster by first multipyling
    the cell value by 100 and then converting it to integer.

    Args:
        float_raster (raster): input raster
        int_raster (raster):
    """

    # init logger
    logger = logging.getLogger(__name__)

    # multiply raster by 1000
    inRaster = Raster(float_raster)
    outTimes = inRaster * 100
    # convert raster to integer
    outInt = Int(outTimes)
    outInt.save(int_raster)


def rasterList_toMosaic(
    raster_list, ouput_gdb, output_name, coord_system, spatial_resolution
):
    """Mosaics a list of rasters to a new 32 bit signed raster dataset using the mean cell values.

    Args:
        raster_list (_type_): _description_
        ouput_gdb (_type_): _description_
        output_name (_type_): _description_
        COORD_SYSTEM (_type_): _description_
        SPATIAL_RESOLUTION (_type_): _description_
    """

    # init logger
    logger = logging.getLogger(__name__)

    output_name = output_name.replace(".", "-")

    arcpy.management.MosaicToNewRaster(
        input_rasters=raster_list,
        output_location=ouput_gdb,
        raster_dataset_name_with_extension=output_name,
        coordinate_system_for_the_raster=coord_system,
        pixel_type="32_BIT_SIGNED",
        cellsize=spatial_resolution,
        number_of_bands=1,
        mosaic_method="MEAN",
        mosaic_colormap_mode="FIRST",
    )


# --------------------------------------------------------------------------- #
# Split Neighbourhoods Functions
# --------------------------------------------------------------------------- #


def split_neighbourhoods(neighbourhood_path, n_field_name, split_neighbourhoods_gdb):
    # split neighbourhoods features into separate features and save them as separate layers in a filegdb

    # init logger
    logger = logging.getLogger(__name__)

    # create a gdb for neighbourhoods
    createGDB_ifNotExists(split_neighbourhoods_gdb)

    # create a list of neighbourhoods
    neighbourhoods_list = []
    with arcpy.da.SearchCursor(neighbourhood_path, n_field_name) as cursor:
        for row in cursor:
            neighbourhoods_list.append(row[0])

    logger.info(f"\tNeighbourhoods:\t{neighbourhoods_list}")

    # split neighbourhoods
    for n in neighbourhoods_list:
        logger.info(f"\tSplitting neighbourhood {n}...")
        arcpy.Select_analysis(
            in_features=neighbourhood_path,
            out_feature_class=os.path.join(split_neighbourhoods_gdb, f"b_{n}"),
            where_clause=f"{n_field_name} = '{n}'",
        )


def get_neighbourhood_list(neighbourhood_path, n_field_name):
    # init logger
    # logger = logging.getLogger(__name__)

    get_list = lambda neighbourhood_path, n_field_name: [
        row[0] for row in arcpy.da.SearchCursor(neighbourhood_path, n_field_name)
    ]
    neighbourhood_list = get_list(neighbourhood_path, n_field_name)

    return sorted(neighbourhood_list)


def round_fields_two_decimals(feature_class, fields_to_round: list):
    """
    Rounds the values in all FLOAT fields in a feature class to two decimal places.

    Args:
        feature_class (str): The path to the feature class.
        field_to_round (list): A list of field names to round.
    """

    # Update the attribute values using the Calculate Field tool
    for field in fields_to_round:
        expression = "round(!{}!, 2)".format(field)
        arcpy.CalculateField_management(feature_class, field, expression, "PYTHON9.3")

    logger.info("Rounding completed.")


def exportPoints_byPolygon(
    point_layer, polygon_layer, selecting_field, output_gdb, output_id_field="point_id"
):
    """Iterate over a polygon layer and for each object select all points WITHIN
    the polygon and export those points to a separate layer based on a value
    in the polygon layer.

    Example:
    Select all points within a neighbourhood and export them to a separate layer
    for each neighbourhood,

    Args:
        point_layer (_type_): input point layer
        polygon_layer (_type_): input polygon layer
        selecting_field (_type_): field name with unique values to classify points.
        ouput_gdb (_type_): output gdb to store point feature layers

    Returns:
        dict: dictionary with KEY: neigbourhood code and VALUE: path to point feature layer
    """
    # dict to store the new layers containing points per neighbourhood
    output_points = {}

    fields = ["OID@", selecting_field]
    # iterate through neighbourhood polygons
    with arcpy.da.SearchCursor(polygon_layer, fields) as cursor:
        for row in cursor:
            # Get the Object ID and neighborhood code for each neighborhood
            n_oid, value = row
            logging.info(
                f"Processing OBJECTID {n_oid}, with {selecting_field}: {value}..."
            )

            # Set the spatial relationship for the Spatial Join
            query = f"{selecting_field} = '{value}'"

            # create bydel layer
            arcpy.MakeFeatureLayer_management(
                in_features=polygon_layer, out_layer=f"temp_{n_oid}", where_clause=query
            )

            output = os.path.join(output_gdb, "b_" + value + "_stems")

            # Perform the Spatial Join between the points and the current neighborhood
            # Keep only the points that are within the neighborhood
            if arcpy.Exists(output):
                arcpy.management.Delete(output)

            output_lyr = arcpy.analysis.SpatialJoin(
                point_layer,
                f"temp_{n_oid}",
                output,
                join_operation="JOIN_ONE_TO_ONE",
                join_type="KEEP_COMMON",
                match_option="WITHIN",
            )

            addField_ifNotExists(output_lyr, output_id_field, "TEXT")
            # add id using selecting_field
            with arcpy.da.UpdateCursor(
                output_lyr, ["OBJECTID", output_id_field, selecting_field]
            ) as cursor:
                for row in cursor:
                    # format id to <bydelcode>_<OBJECTID>
                    row[1] = "id_" + str(value) + "_" + str(row[0])
                    cursor.updateRow(row)

            # Add the output feature layer to the dictionary with the neighborhood name as the key
            output_points[value] = output_lyr

    return output_points


def exists_and_has_features(fc):
    """Checks if a feature class exists and contains any features.

    Args:
        fc: The feature class to check.

    Returns:
        True if the feature class exists and contains any features, False otherwise.
    """

    if not arcpy.Exists(fc):
        return False

    count = arcpy.GetCount_management(fc)
    if count == 0:
        return False

    return True


# Get a list of all layers in the current map
def clear_selection():
    """ONLY WORKS IF ARCGIS IS OPENED"""
    active_project = arcpy.mp.ArcGISProject("CURRENT")
    map = active_project.listMaps()[0]
    for layer in map.listLayers():
        arcpy.SelectLayerByAttribute_management(layer, "CLEAR_SELECTION")

    # for table in map.listTables():
    # arcpy.SelectLayerByAttribute_management(table, "CLEAR_SELECTION")


def keep_fields(input_fc, fields_to_keep):
    fields = arcpy.ListFields(input_fc)

    fields_to_keep = [field.lower() for field in fields_to_keep]

    # delete all fields except the following
    fields_to_delete = []
    for field in fields:
        if field.name.lower() not in fields_to_keep:
            fields_to_delete.append(field.name)

    # if list is not empty list delete fields
    if fields_to_delete != []:
        arcpy.DeleteField_management(input_fc, fields_to_delete)


if __name__ == "__main__":
    logger = logging.getLogger(__name__)
