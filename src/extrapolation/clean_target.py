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
    target_trees = catalog[f"{municipality}_trees"]["target_trees"]

    # load target data from PARQUET if exist otherwise CSV
    if os.path.exists(target_trees["filepath_parquet"]):
        df_target = pd.read_parquet(target_trees["filepath_parquet"])
    else:
        df_target = pd.read_csv(target_trees["filepath_csv"])
    return df_target


def clean_target_cols(df_target):
    parameters = load_parameters()

    # convert all cols to lowercase
    df_target.columns = df_target.columns.str.lower()

    # set cols to numeric if not already
    if parameters["municipality"] == "oslo":
        cols_numeric = parameters["cols_target_oslo"]
    else:
        cols_numeric = parameters["cols_target"]

    for col in cols_numeric:
        if col in df_target.columns:
            df_target[col] = pd.to_numeric(df_target[col], errors="coerce")
        if col not in df_target.columns:
            df_target.loc[:, col] = None

    # round all numeric cols to 2 decimals
    df_target[cols_numeric] = df_target[cols_numeric].round(2)

    if parameters["municipality"] == "oslo":
        cols_to_keep = parameters["cols_ref_oslo"]
    else:
        cols_to_keep = parameters["cols_ref"]

    # create new columns, if not exist
    for col in cols_to_keep:
        if col not in df_target.columns:
            df_target.loc[:, col] = None

    # remove cols not in cols_to_keep
    df_target = df_target[cols_to_keep]

    return df_target


def clean_target_rows(df_target):
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
    cols_numeric = df_target.select_dtypes(include=["float64", "int64"]).columns
    df_target[cols_numeric] = df_target[cols_numeric].clip(lower=0)

    return df_target


def fill_missing_species(df_target, df_summary):
    """Fill missing species in df_target using df_summary."""

    # load summary into df
    df_summary = pd.read_csv(df_summary)
    print("Sum of Perc:", df_summary["Perc"].sum())
    # normalize Perc to probabilities (100% = 1)
    df_summary["Perc"] = df_summary["Perc"] / df_summary["Perc"].sum()

    # fil no data values in test_df['species'] by using
    # the probability distribution of df['species']
    df_target["norwegian_name"] = df_target["norwegian_name"].apply(
        lambda x: np.random.choice(df_summary["norwegian_name"], p=df_summary["Perc"])
        if pd.isnull(x)
        else x
    )
    return df_target


def encode_and_rename(df, column, prefix):
    """Helper function to encode and rename a dataframe column."""
    df[column] = df[column].astype("category")
    encoded_df = pd.get_dummies(df[column], prefix=prefix)
    encoded_cols = [col.replace(prefix, "").lower() for col in encoded_df.columns]
    encoded_df.columns = encoded_cols
    return pd.concat([df, encoded_df], axis=1)


def encode_species(df_ref):
    """Encode norwegian_name and species using one-hot encoding."""
    df_ref = encode_and_rename(df_ref, "norwegian_name", "treslag_")
    return df_ref


def export_target(df_target):
    # export target data to csv
    parameters = load_parameters()
    municipality = parameters["municipality"]

    catalog = load_catalog()
    target_trees = catalog[f"{municipality}_trees"]["target_trees"]
    df_target.to_csv(target_trees["filepath_target"], index=False, encoding="utf-8")
    df_target.to_parquet(target_trees["filepath_parquet"], index=False)
    return


def main():
    # set up logging
    logger = logging.getLogger(__name__)
    params = load_parameters()
    municipality = params["municipality"]
    catalog = load_catalog()
    target_path = catalog[f"{municipality}_trees"]["target_trees"]["filepath_parquet"]
    logger.info(f"Load reference and target data for municipality: {municipality}")
    print(target_path)
    # if file not exist then create it
    if not os.path.exists(target_path):
        logger.info(f"Target data not found. Creating new target data.")
        df_target = load_target()

        # CLEAN TARGET
        # ------------
        df_target = clean_target_cols(df_target)
        df_target = clean_target_rows(df_target)

        # ENCODE SPECIES
        # --------------
        df_summary = catalog[f"{municipality}_trees"]["reference_trees"][
            "filepath_species_summary"
        ]

        print(df_summary)
        df_target = fill_missing_species(df_target, df_summary)
        df_target = encode_species(df_target)

        # EXPORT TARGET
        # -------------
        export_target(df_target)
    else:
        df_target = pd.read_parquet(target_path)
        export_target(df_target)

    return df_target


if __name__ == "__main__":
    main()
