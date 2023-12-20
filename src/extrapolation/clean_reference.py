# nodes.py
import logging
import os

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
def load_reference() -> pd.DataFrame:
    """Load reference data."""

    # set up logging
    parameters = load_parameters()
    municipality = parameters["municipality"]

    catalog = load_catalog()
    raw_trees = catalog[f"{municipality}_extrapolation"]["raw_trees"]

    # load raw data from PARQUET if exist otherwise CSV
    if os.path.exists(raw_trees["filepath_parquet"]):
        df_ref = pd.read_parquet(raw_trees["filepath_parquet"])
    else:
        df_ref = pd.read_csv(raw_trees["filepath_csv"])
    return df_ref


@logger_decorator
def load_lookup() -> pd.DataFrame:
    """Load municipality specific lookup data from excel."""

    parameters = load_parameters()
    municipality = parameters["municipality"]

    catalog = load_catalog()
    lookup = catalog[f"{municipality}_extrapolation"]["lookup"]

    # read lookup from excel, sheetname
    # read with encoding to utf-8

    # df_lookup = pd.read_excel(lookup["filepath"], sheet_name=lookup["sheet_name"])
    df_lookup = pd.read_csv(lookup["filepath_csv"])
    return df_lookup


def clean_reference_cols(df_ref, df_lookup):
    """
    Clean referance data.
    - rename cols using lookup
    - remove irrelevant cols
    - subset cols using params

    Parameters
    ----------
    df_ref : _type_
        _description_
    df_lookup : _type_
        _description_
    """

    municipality = load_parameters()["municipality"]

    # 1. CLEAN COLUMNS
    # ----------------
    if municipality == "oslo":
        if df_lookup is not None:
            if "name_python" in df_lookup.columns:
                df_lookup = df_lookup.dropna(subset=["name_python"])
                df_lookup = df_lookup[df_lookup["name_python"] != ""]

            lookup_cols = df_lookup["name"].tolist()
            lookup_cols = [col for col in df_ref.columns if col in lookup_cols]

            # remove cols not in cols_to_keep
            df_ref = df_ref[lookup_cols]

            # rename cols using lookup name:name_python
            col_name_mapping = dict(zip(df_lookup["name"], df_lookup["name_python"]))
            df_ref.rename(columns=col_name_mapping, inplace=True)

    # set int cols
    # if col in int_col set to int
    parameters = load_parameters()
    cols_int = parameters["cols_int"]
    for col in cols_int:
        if col in df_ref.columns:
            # convert str to flt
            df_ref[col] = pd.to_numeric(df_ref[col], errors="coerce")
            # convert flt to int if NA set to NA
            df_ref[col] = df_ref[col].astype(np.int64, errors="ignore")

    cols_float = parameters["cols_float"]
    for col in cols_float:
        if col in df_ref.columns:
            # convert to numeric if possible otherwise set to NaN
            df_ref[col] = pd.to_numeric(df_ref[col], errors="coerce")

    # create new columns, if not exist
    municipality = parameters["municipality"]
    cols_to_keep = parameters[municipality]["cols_ref"]
    for col in cols_to_keep:
        if col not in df_ref.columns:
            df_ref.loc[:, col] = None

    # remove cols not in cols_to_keep
    df_ref = df_ref[cols_to_keep]

    return df_ref


def clean_reference_rows(df_ref, col_species):
    """
    Clean referance data.
    - remove rows with missing values for totben_cap
    - fill rows with missing values for dbh and height
        - dbh = 4.04 * height^0.82
        - dbh = (crown_diam^2.63)/(3.48^2.63)
        - height = (dbh*1.22)/(4.04^1.22)

    Parameters
    ----------
    df_ref : _type_
        _description_
    col_species : _type_
        _description_

    Returns
    -------
    _type_
        _description_
    """
    # 1. remove values with itree_spec = 0
    if "itree_spec" in df_ref.columns:
        df_ref = df_ref[df_ref["itree_spec"] != 0]

    # 2. fill rows with missing values
    # if dbh is  null and height is not null
    if "dbh" in df_ref.columns and "height_total_tree" in df_ref.columns:
        mask = (df_ref["dbh"].isnull()) & (df_ref["height_total_tree"].notnull())
        df_ref.loc[mask, "dbh"] = 4.04 * df_ref.loc[mask, "height_total_tree"] ** 0.82
        df_ref.loc[mask, "dbh_origin"] = "dbh = 4.04 * height^0.82"

    # if dbh is  null and crown_diam is not null
    if "dbh" in df_ref.columns and "crown_diam" in df_ref.columns:
        mask = (df_ref["dbh"].isnull()) & (df_ref["crown_diam"].notnull())
        df_ref.loc[mask, "dbh"] = (df_ref.loc[mask, "crown_diam"] ** 2.63) / (
            3.48**2.63
        )
        df_ref.loc[mask, "dbh_origin"] = "dbh = (crown_diam^2.63)/(3.48^2.63)"
    # if height is  null and dbh is not null
    if "height_total_tree" in df_ref.columns and "dbh" in df_ref.columns:
        mask = (df_ref["height_total_tree"].isnull()) & (df_ref["dbh"].notnull())
        df_ref.loc[mask, "height_total_tree"] = (df_ref.loc[mask, "dbh"] * 1.22) / (
            4.04**1.22
        )
        df_ref.loc[
            mask, "height_origin"
        ] = "height_total_tree = (dbh*1.22)/(4.04**1.22)"

    # totben_cap_ca = totben_cap/crown_area
    if "totben_cap" in df_ref.columns and "crown_area" in df_ref.columns:
        df_ref["totben_cap_ca"] = df_ref["totben_cap"] / df_ref["crown_area"]

    # Replace any potential NaN values resulting from the calculations
    df_ref.replace([np.inf, -np.inf], np.nan)

    # if rows < 0 in cols numeric then set to 0
    params = load_parameters()
    cols_float = params["cols_float"]
    for col in cols_float:
        df_ref.loc[:, col] = df_ref.loc[:, col].clip(lower=0)

    # remove rows with missing values for
    # col_species, dbh, height_total_tree, crown_area or pollution_zone
    cols_to_check = [
        col_species,
        "dbh",
        "height_total_tree",
        "crown_area",
        "pollution_zone",
    ]
    df_ref = df_ref.dropna(subset=cols_to_check)

    # set values in col species to lower case
    df_ref[col_species] = df_ref[col_species].str.lower()

    # round numeric cols to 2 decimals
    cols_numeric = df_ref.select_dtypes(include=[np.number]).columns.tolist()
    df_ref[cols_numeric] = df_ref[cols_numeric].round(2)

    return df_ref


def calc_summary(data, x, classify_other=False):
    # drop "" and " " and "NA"
    data = data[data[x].notna() & (data[x] != "") & (data[x] != " ")]

    # create summary dataframe df[x, n, perc]
    summary = data[x].value_counts().reset_index()
    summary.columns = [x, "n"]
    summary["Probability"] = summary["n"] / summary["n"].sum()
    summary["Perc"] = round(summary["Probability"] * 100, 2)
    summary = summary.sort_values("Perc", ascending=False)
    probability_sum = abs(summary["Probability"].sum() - 1)
    if not np.isclose(probability_sum, 1.0, atol=1e-8):
        raise ValueError("Error: Probability SUM != 1")

    data_summary = summary.drop(columns="Probability")

    if classify_other:
        other = data_summary[data_summary["Perc"] < 2].sum(numeric_only=True)
        other[x] = "Andre treslag*"
        data_summary = data_summary[data_summary["Perc"] >= 2]
        data_summary = data_summary.append(other, ignore_index=True)

    return data_summary


def plot_summary(data, x, y, title, xlabel, ylabel, filename):
    import matplotlib.pyplot as plt
    import seaborn as sns

    # plot histogram
    fig, ax = plt.subplots(figsize=(30, 5))
    sns.barplot(x=x, y=y, data=data, ax=ax, color="darkgreen")
    ax.set_title(title, fontweight="ultralight", fontsize=20)
    ax.set_xlabel(xlabel, fontweight="bold")
    ax.set_ylabel(ylabel, fontweight="bold")
    plt.xticks(rotation=45, fontweight="ultralight")
    plt.yticks(fontsize=10)
    plt.savefig(filename)


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
    """Encode species using one-hot encoding."""
    df = encode_and_rename(df, col_species, "SP")
    return df


def export_reference(df_ref, df_species_summary):
    # export reference data to csv
    import numpy as np

    parameters = load_parameters()
    municipality = parameters["municipality"]

    catalog = load_catalog()
    cols_int = parameters["cols_int"]
    cols_float = parameters["cols_float"]

    for col in cols_int:
        if col in df_ref.columns:
            df_ref[col] = df_ref[col].astype(np.int64)

    for col in cols_float:
        if col in df_ref.columns:
            df_ref[col] = pd.to_numeric(df_ref[col], errors="coerce")
            df_ref[col] = df_ref[col].round(2)

    ref_trees = catalog[f"{municipality}_extrapolation"]["reference"]
    df_ref.to_csv(ref_trees["filepath_csv"], index=False, encoding="utf-8")

    summary_path = catalog[f"{municipality}_extrapolation"]["species_summary"][
        "filepath"
    ]
    df_species_summary.to_csv(summary_path, index=False, encoding="utf-8")
    return df_ref


def main(col_id, col_species):
    # set up logging
    logger = logging.getLogger(__name__)
    params = load_parameters()
    catalog = load_catalog()
    municipality = params["municipality"]
    logger.info(f"Load reference data for municipality: {municipality}")

    # if file not exist then create it
    if not os.path.exists(
        catalog[f"{municipality}_extrapolation"]["reference"]["filepath_csv"]
    ):
        logger.info("Reference data not found, creating it")
        # load reference and lookup data
        df_ref = load_reference()
        if municipality == "oslo":
            df_lookup = load_lookup()

        # CLEAN REFERENCE
        # ---------------
        df_ref = clean_reference_cols(df_ref, df_lookup=None)
        df_ref = clean_reference_rows(df_ref, col_species)

        # ENCODE SPECIES
        # --------------
        df_species_summary = calc_summary(df_ref, col_species, classify_other=False)
        filename = catalog[f"{municipality}_extrapolation"]["species_summary"][
            "img_path"
        ]
        plot_summary(
            df_species_summary,
            x=col_species,
            y="Perc",
            title="Treslagsfordeling",
            xlabel="Treslag",
            ylabel="Sannsynlighet (%)",
            filename=filename,
        )
        df_ref = encode_species(df_ref, col_species)

        # EXPORT REFERENCE
        # ----------------
        df_ref = export_reference(df_ref, df_species_summary)
    else:
        df_ref = pd.read_csv(
            catalog[f"{municipality}_extrapolation"]["reference"]["filepath_csv"]
        )

    # log info
    logger.info(f"Reference data shape: {df_ref.shape}")
    logger.info(f"Reference data columns: {df_ref.columns.tolist()}")
    logger.info(f"Reference data head: {df_ref.head()}")
    return df_ref


if __name__ == "__main__":
    main(col_id="tree_id", col_species="taxon_genus")
