import os

os.environ["USE_PYGEOS"] = "0"
import geopandas as gpd
import pandas as pd

from src.config.config import load_catalog, load_parameters


def merge_csv(col_id, col_species):
    # export target data to csv
    parameters = load_parameters()
    municipality = parameters["municipality"]

    catalog = load_catalog()
    csv_folder = catalog[f"{municipality}_extrapolation"]["output"]["filepath_csv"]

    csv_files = [
        "totben_cap",
        "co2_storage_kg",
        "co2_seq_kg_yr",
        "runoff_m3",
        # "pollution_no2",
        # "pollution_pm25",
        # "pollution_so2",
        "pollution_g",
    ]

    dfs = {}

    for file in csv_files:
        dfs[file] = pd.read_csv(
            os.path.join(csv_folder, f"{municipality}_{file}_predicted.csv"),
            low_memory=False,
        )

    # drop cols except for id and value
    for col, df in dfs.items():
        if col == "totben_cap":
            df = df[
                [
                    col_id,
                    col_species,
                    "species_origin",
                    "delomradenummer",
                    "grunnkretsnummer",
                    "dbh",
                    "dbh_origin",
                    "height_total_tree",
                    "height_origin",
                    "crown_area",
                    "crown_diam",
                    "crown_origin",
                    "pollution_zone",
                    "totben_cap",
                    "totben_cap_ca",
                ]
            ]
        else:
            df = df[[col_id, col]]

        # update dict
        dfs[col] = df
        print(df.shape)
        print(df.head(2))

    # merge all dfs based on id (13504, 15 ) + (13504, 2) +  (13504, 2) + (13504, 2) + (13504, 2) + > (13504, 23)

    df_merged = dfs["totben_cap"]
    # if duplicates in col_id print ERROR
    if df_merged[col_id].duplicated().any():
        print("ERROR: duplicates in col_id")
        print(df_merged[df_merged[col_id].duplicated()])
        return

    for col, df in dfs.items():
        if col != "totben_cap":
            print(f"Merge {col} with shape {df.shape} to df_merged")
            df_merged = df_merged.merge(df, on=col_id)

    print(df_merged.shape)

    # calculate
    # totben_cap_ca = totben_cap / crown_area
    df_merged["totben_cap_ca"] = df_merged["totben_cap"] / df_merged["crown_area"]
    df_merged = df_merged.round(2)
    print(df_merged.head(2))

    # export to csv
    df_merged.to_csv(
        os.path.join(csv_folder, f"{municipality}_extrapolation_results.csv"),
        index=False,
    )
    return


def merge_geojson(col_id):
    # export target data to csv
    parameters = load_parameters()
    municipality = parameters["municipality"]

    catalog = load_catalog()
    csv_folder = catalog[f"{municipality}_extrapolation"]["output"]["filepath_csv"]

    filename = f"{municipality}_extrapolation_results.csv"
    df = pd.read_csv(os.path.join(csv_folder, filename))

    geojson_path = catalog[f"{municipality}_extrapolation"]["raw_crowns"][
        "filepath_geojson"
    ]
    gdf = gpd.read_file(geojson_path)

    # merge on id
    gdf_merged = gdf.merge(df, on=col_id)
    print(gdf_merged.head())

    # export to geojson
    gdf_merged.to_file(
        os.path.join(csv_folder, f"{municipality}_extrapolation_results.geojson"),
        driver="GeoJSON",
    )
    return


def create_summary(col_species):
    # read results csv
    parameters = load_parameters()
    municipality = parameters["municipality"]

    catalog = load_catalog()
    csv_folder = catalog[f"{municipality}_extrapolation"]["output"]["filepath_csv"]

    filename = f"{municipality}_extrapolation_results.csv"
    df = pd.read_csv(os.path.join(csv_folder, filename))

    categorical_vars = [col_species, "pollution_zone"]
    continuous_vars = [
        "dbh",
        "height_total_tree",
        "crown_area",
        "totben_cap",
        "totben_cap_ca",
        "co2_storage_kg",
        "co2_seq_kg_yr",
        "runoff_m3",
        # "pollution_no2",
        # "pollution_pm25",
        # "pollution_so2",
        "pollution_g",
    ]

    # SUMMARY STAT BUILT-UP ZONE
    # ---------------------------
    # count mean std min 25% 50% 75% max
    # median sum
    df_summary = df[continuous_vars].describe()
    df_summary.loc["median"] = df[continuous_vars].median()
    df_summary.loc["sum"] = df[continuous_vars].sum()
    df_summary = df_summary.round(2)

    # export to csv
    df_summary.to_csv(
        os.path.join(csv_folder, f"{municipality}_summary_ES_built_up_zone.csv"),
        index=True,
    )
    print(df_summary)

    # SUM OF ES PER DISTRICTS
    # -----------------------
    df_sum = df.groupby(["grunnkretsnummer"]).sum()
    df_sum = df_sum[continuous_vars]
    df_sum = df_sum.reset_index()
    df_sum = df_sum.rename(columns={"grunnkretsnummer": "district_id"})

    # last row is sum of all districts
    df_sum.loc["sum"] = df_sum.sum()
    print(df_sum.head())

    # export to csv
    df_sum.to_csv(
        os.path.join(csv_folder, f"{municipality}_sum_ES_per_district.csv"),
        index=False,
    )

    if municipality == "oslo":
        # SUMMARY STAT SCHOOLS
        # --------------------
        df_schools = df[df["teig_undervisning"] == 1]

        df_schools_summary = df_schools[continuous_vars].describe()
        df_schools_summary.loc["median"] = df_schools[continuous_vars].median()
        df_schools_summary.loc["sum"] = df_schools[continuous_vars].sum()
        df_schools_summary = df_schools_summary.round(2)

        print(df_schools_summary)

        # export to csv
        df_schools_summary.to_csv(
            os.path.join(csv_folder, f"{municipality}_summar_ES_schools.csv"),
            index=True,
        )

        # read school IDs
        school_ids = pd.read_csv(
            os.path.join(csv_folder, "oslo_school_ids.csv"), header=None
        )
        # SUM OF ES PER SCHOOL
        # --------------------

        df_schools_sum = df_schools.groupby(["id"]).sum()
        df_schools_sum = df_schools_sum[continuous_vars]
        df_schools_sum = df_schools_sum.reset_index()
        df_schools_sum = df_schools_sum.rename(columns={"id": "school_id"})

    return
