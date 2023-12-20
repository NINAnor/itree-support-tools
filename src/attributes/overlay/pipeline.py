from nodes import land_use, neighbourhood, privat_public, street_tree


def overlay(
    v_stem_path,
    v_crown_path,
    filegdb_path,
    v_neighbourhoods,
    v_area_data,
    v_property_data,
):
    neighbourhood(v_stem_path, v_crown_path, filegdb_path, v_neighbourhoods)
    street_tree(v_stem_path, v_crown_path, filegdb_path, v_area_data)
    privat_public(v_stem_path, v_crown_path, filegdb_path, v_property_data)
    land_use(v_stem_path, v_crown_path, filegdb_path, v_area_data)
    return


if __name__ == "__main__":
    pass
