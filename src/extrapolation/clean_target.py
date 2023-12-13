# nodes.py
import os
import logging
import numpy as np
import pandas as pd
from src.config.config import load_catalog, load_parameters


def logger_decorator(func):
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(__name__)
        logger.info(f"Running {func.__name__}")
        return func(*args, **kwargs)

    return wrapper


@logger_decorator
def load_target() -> pd.DataFrame:
    """Load target data."""

    # set up logging
    parameters = load_parameters()
    municipality = parameters["municipality"]

    catalog = load_catalog()
    raw_crowns = catalog[f"{municipality}_extrapolation"]["raw_crowns"]

    # load target data from PARQUET if exist otherwise CSV
    if os.path.exists(raw_crowns["filepath_parquet"]):
        df_target = pd.read_parquet(raw_crowns["filepath_parquet"])
    else:
        df_target = pd.read_csv(raw_crowns["filepath_csv"])
    return df_target


def clean_target_cols(df_target, col_id):
    parameters = load_parameters()

    # convert all colnames to lowercase except col_id
    df_target.columns = [
        col.lower() if col != "col ID" else col for col in df_target.columns
    ]

    # set int cols
    # if col in int_col set to in
    cols_int = parameters["cols_int"]
    for col in cols_int:
        if col in df_target.columns:
            # convert str to flt
            df_target[col] = pd.to_numeric(df_target[col], errors="coerce")
            # convert flt to int if NA set to NA
            df_target[col] = df_target[col].astype(np.int64, errors="ignore")

    cols_float = parameters["cols_float"]
    for col in cols_float:
        if col in df_target.columns:
            # convert to numeric if possible otherwise set to NaN
            df_target[col] = pd.to_numeric(df_target[col], errors="coerce")
            # round all numeric cols to 2 decimals
            df_target[col] = df_target[col].round(2)

    # create new columns, if not exist
    municipality = parameters["municipality"]
    cols_to_keep = parameters[municipality]["cols_target"]
    for col in cols_to_keep:
        if col not in df_target.columns:
            df_target.loc[:, col] = None

    # remove cols not in cols_to_keep
    df_target = df_target[cols_to_keep]

    return df_target


def clean_target_rows(df_target, col_species):
    # fill rows with missing values
    # if dbh is  null and height is not null
    if "dbh" in df_target.columns and "height_total_tree" in df_target.columns:
        mask = (df_target["dbh"].isnull()) & (df_target["height_total_tree"].notnull())
        df_target.loc[mask, "dbh"] = (
            4.04 * df_target.loc[mask, "height_total_tree"] ** 0.82
        )
        df_target.loc[mask, "dbh_origin"] = "dbh = 4.04 * height^0.82"

    # if dbh is  null and crown_diam is not null
    if "dbh" in df_target.columns and "crown_diam" in df_target.columns:
        mask = (df_target["dbh"].isnull()) & (df_target["crown_diam"].notnull())
        df_target.loc[mask, "dbh"] = (df_target.loc[mask, "crown_diam"] ** 2.63) / (
            3.48**2.63
        )
        df_target.loc[mask, "dbh_origin"] = "dbh = (crown_diam^2.63)/(3.48^2.63)"

    # if height is  null and dbh is not null
    if "height_total_tree" in df_target.columns and "dbh" in df_target.columns:
        mask = (df_target["height_total_tree"].isnull()) & (df_target["dbh"].notnull())
        df_target.loc[mask, "height_total_tree"] = (
            df_target.loc[mask, "dbh"] * 1.22
        ) / (4.04**1.22)
        df_target.loc[
            mask, "height_origin"
        ] = "height_total_tree = (dbh*1.22)/(4.04**1.22)"

    # Replace any potential NaN values resulting from the calculations
    df_target.replace([np.inf, -np.inf], np.nan)

    # if rows < 0 in cols numeric then set to 0
    params = load_parameters()
    cols_float = params["cols_float"]
    for col in cols_float:
        df_target.loc[:, col] = df_target.loc[:, col].clip(lower=0)

    # set values in col species to lower case
    df_target[col_species] = df_target[col_species].str.lower()

    # round numeric cols to 2 decimals
    cols_numeric = df_target.select_dtypes(include=[np.number]).columns.tolist()
    df_target[cols_numeric] = df_target[cols_numeric].round(2)

    return df_target


def fill_missing_species(df_target, df_summary, col_species):
    """Fill missing species in df_target using df_summary."""

    # load summary into df
    df_summary = pd.read_csv(df_summary)
    print("Sum of Perc:", df_summary["Perc"].sum())
    # normalize Perc to probabilities (100% = 1)
    df_summary["Perc"] = df_summary["Perc"] / df_summary["Perc"].sum()

    # fil no data values in test_df['species'] by using
    # the probability distribution of df['species']
    df_target[col_species] = df_target[col_species].apply(
        lambda x: np.random.choice(df_summary[col_species], p=df_summary["Perc"])
        if pd.isnull(x)
        else x
    )

    # species_origin to str and fill missing values
    # convert int to string (1 -> "1")

    df_target["species_origin"] = df_target["species_origin"].astype(str)
    df_target["species_origin"] = df_target["species_origin"].apply(
        lambda x: "estimated by probability distribution" if pd.isnull(x) else str(x)
    )

    return df_target


def encode_and_rename(df, column, prefix):
    """Helper function to encode and rename a dataframe column."""
    df[column] = df[column].astype("category")
    encoded_df = pd.get_dummies(df[column], prefix=prefix)

    # ensure all spaces in col names are replaced with "_"
    encoded_df.columns = encoded_df.columns.str.replace(" ", "_")

    # set all encoded_cols to int
    encoded_df = encoded_df.astype(np.int64)
    return pd.concat([df, encoded_df], axis=1)


def encode_species(df, col_species):
    """Encode norwegian_name and species using one-hot encoding."""
    df = encode_and_rename(df, col_species, "SP")
    return df


def export_target(df_target):
    # export target data to csv
    parameters = load_parameters()
    municipality = parameters["municipality"]

    catalog = load_catalog()
    target_trees = catalog[f"{municipality}_extrapolation"]["target"]
    df_target.to_csv(target_trees["filepath_csv"], index=False, encoding="utf-8")
    df_target.to_parquet(target_trees["filepath_parquet"], index=False)
    return


def main(col_id, col_species):
    # set up logging
    logger = logging.getLogger(__name__)
    params = load_parameters()
    municipality = params["municipality"]
    catalog = load_catalog()
    target_path = catalog[f"{municipality}_extrapolation"]["target"]["filepath_parquet"]
    logger.info(f"Load target data for municipality: {municipality}")

    # if file not exist then create it
    if not os.path.exists(target_path):
        logger.info(f"Target data not found. Creating new target data.")
        df_target = load_target()

        # CLEAN TARGET
        # ------------
        df_target = clean_target_cols(df_target, col_id)
        df_target = clean_target_rows(df_target, col_species)

        # ENCODE SPECIES
        # --------------
        df_summary = catalog[f"{municipality}_extrapolation"]["species_summary"][
            "filepath"
        ]

        print(df_summary)
        df_target = fill_missing_species(df_target, df_summary, col_species)
        df_target = encode_species(df_target, col_species)

        # EXPORT TARGET
        # -------------
        export_target(df_target)
    else:
        df_target = pd.read_parquet(target_path)

    return df_target


if __name__ == "__main__":
    main(col_id="OBJECTID", col_species="taxon_genus")
