import geopandas as gpd
import pandas as pd

from src.config.config import load_catalog, load_parameters


def join_to_geojson(col_id, csv, geojson):
    # export target data to csv
    parameters = load_parameters()
    municipality = parameters["municipality"]

    catalog = load_catalog()
    output_path = catalog[f"{municipality}_extrapolation"]["target"]

    df_csv = pd.read_csv(csv)
    gdf_geojson = gpd.read_file(geojson)

    gdf_merged = gdf_geojson.merge(df_csv, on=col_id)
    print(gdf_merged.head())

    gdf_merged.to_file(output_path, driver="GeoJSON")
    return
