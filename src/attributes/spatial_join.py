# Import system modules
import os

import arcpy

# TODO load data_paths from catalog.yaml
# from src import INTERIM_PATH, ADMIN_GDB


def spatial_join(
    target_features,
    overlay_source,
    outfc,
    join_field,
    target_field,
    match_option="HAVE_THEIR_CENTER_IN",
):
    """Uses spatial join and field mapping to join overlay sources to the crown layer.

    Args:
        v_crown (_type_): _description_
        overlay_data_source (_type_): _description_
        outfc (_type_): _description_
        join_field (_type_): _description_
        target_field (_type_): _description_
    """
    joinFeatures = overlay_source

    # Create a new fieldmappings and add the two input feature classes.
    fieldmappings = arcpy.FieldMappings()
    fieldmappings.addTable(target_features)
    fieldmappings.addTable(joinFeatures)

    # First get the fieldmap for the join field in the target table
    FieldIndex = fieldmappings.findFieldMapIndex(join_field)
    fieldmap = fieldmappings.getFieldMap(FieldIndex)

    # Get the output field's properties as a field object from the join table
    field = fieldmap.outputField

    # Rename the field and pass the updated field object back into the field map
    field.name = target_field
    field.aliasName = target_field
    fieldmap.outputField = field

    fieldmappings.replaceFieldMap(FieldIndex, fieldmap)

    # Delete fields that are no longer applicable, such as city CITY_NAME and CITY_FIPS
    # as only the first value will be used by default
    # x = fieldmappings.findFieldMapIndex("n_grunnkrets")
    # fieldmappings.removeFieldMap(x)
    # y = fieldmappings.findFieldMapIndex("objtype")
    # fieldmappings.removeFieldMap(y)

    # Run the Spatial Join tool, using the defaults for the join operation and join type
    arcpy.analysis.SpatialJoin(
        target_features=target_features,
        join_features=joinFeatures,
        out_feature_class=outfc,
        join_operation="JOIN_ONE_TO_ONE",
        join_type="KEEP_ALL",
        field_mapping=fieldmappings,
        match_option=match_option,
        search_radius=None,
        distance_field_name="",
    )


if __name__ == "__main__":
    filegdb_path = os.path.join(INTERIM_PATH, "itree_attributes", "itree_trees.gdb")
    v_crown_path = os.path.join(filegdb_path, "itree_crowns")

    v_neighbourhoods = os.path.join(ADMIN_GDB, "bydeler")
    out_fc_neigb = os.path.join(filegdb_path, "itree_crowns_neighbourhoods")

    join_field = "bydelnummer"
    target_field = "nb_code"

    spatial_join(v_crown_path, v_neighbourhoods, out_fc_neigb, join_field, target_field)
