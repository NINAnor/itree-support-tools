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
def load_reference() -> pd.DataFrame:
    """Load reference data."""

    # set up logging
    parameters = load_parameters()
    municipality = parameters["municipality"]

    catalog = load_catalog()
    ref_trees = catalog[f"{municipality}_trees"]["reference_trees"]

    # load reference data from PARQUET if exist otherwise CSV
    if os.path.exists(ref_trees["filepath_parquet"]):
        df_ref = pd.read_parquet(ref_trees["filepath_parquet"])
    else:
        df_ref = pd.read_csv(ref_trees["filepath_csv"])
    return df_ref


@logger_decorator
def load_lookup() -> pd.DataFrame:
    """Load municipality specific lookup data from excel."""

    parameters = load_parameters()
    municipality = parameters["municipality"]

    catalog = load_catalog()
    lookup = catalog[f"{municipality}_trees"]["lookup"]

    # read lookup from excel, sheetname
    df_lookup = pd.read_excel(lookup["filepath"], sheet_name=lookup["sheet_name"])

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

    # 1. CLEAN COLUMNS
    # ----------------
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
    print(df_ref.head())
    # from parameters get cols to keep
    parameters = load_parameters()
    if parameters["municipality"] == "oslo":
        cols_to_keep = parameters["cols_ref_oslo"]
    else:
        cols_to_keep = parameters["cols_ref"]

    # create new columns, if not exist
    for col in cols_to_keep:
        if col not in df_ref.columns:
            df_ref.loc[:, col] = None

    # remove cols not in cols_to_keep
    df_ref = df_ref[cols_to_keep]

    # set cols to numeric if not already
    if parameters["municipality"] == "oslo":
        cols_numeric = parameters["cols_target_oslo"]
    else:
        cols_numeric = parameters["cols_target"]

    for col in cols_numeric:
        if col in df_ref.columns:
            df_ref[col] = pd.to_numeric(df_ref[col], errors="coerce")

    # round all numeric cols to 2 decimals
    df_ref[cols_numeric] = df_ref[cols_numeric].round(2)

    return df_ref


def clean_reference_rows(df_ref, df_lookup):
    # 1. remove values with itree_spec = 0
    if "itree_spec" in df_ref.columns:
        df_ref = df_ref[df_ref["itree_spec"] != 0]

    print(df_ref.head())
    # 2. fill rows with missing values
    # if dbh is  null and height is not null
    if "dbh" in df_ref.columns and "height_total_tree" in df_ref.columns:
        mask = (df_ref["dbh"].isnull()) & (df_ref["height_total_tree"].notnull())
        df_ref.loc[mask, "dbh"] = 4.04 * df_ref.loc[mask, "height_total_tree"] ** 0.82
        df_ref.loc[mask, "dbh_origin"] = "dbh = 4.04 * height^0.82"

    print(df_ref["dbh"].head())
    # if dbh is  null and crown_diam is not null
    if "dbh" in df_ref.columns and "crown_diam" in df_ref.columns:
        mask = (df_ref["dbh"].isnull()) & (df_ref["crown_diam"].notnull())
        df_ref.loc[mask, "dbh"] = (df_ref.loc[mask, "crown_diam"] ** 2.63) / (
            3.48**2.63
        )
        df_ref.loc[mask, "dbh_origin"] = "dbh = (crown_diam^2.63)/(3.48^2.63)"
    print(df_ref["dbh"].head())
    # if height is  null and dbh is not null
    if "height_total_tree" in df_ref.columns and "dbh" in df_ref.columns:
        mask = (df_ref["height_total_tree"].isnull()) & (df_ref["dbh"].notnull())
        df_ref.loc[mask, "height_total_tree"] = (df_ref.loc[mask, "dbh"] * 1.22) / (
            4.04**1.22
        )
        df_ref.loc[
            mask, "height_origin"
        ] = "height_total_tree = (dbh*1.22)/(4.04**1.22)"
    print(df_ref["height_total_tree"].head())
    # Replace any potential NaN values resulting from the calculations
    df_ref.replace([np.inf, -np.inf], np.nan)
    print(df_ref.head())

    # if rows < 0 in cols numeric then set to 0
    cols_numeric = df_ref.select_dtypes(include=["float64", "int64"]).columns
    df_ref[cols_numeric] = df_ref[cols_numeric].clip(lower=0)

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

    if abs(summary["Probability"].sum() - 1) > 1e-8:
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
    encoded_cols = [col.replace(prefix, "").lower() for col in encoded_df.columns]
    encoded_df.columns = encoded_cols
    return pd.concat([df, encoded_df], axis=1)


def encode_species(df_target):
    """Encode norwegian_name and species using one-hot encoding."""
    df_target = encode_and_rename(df_target, "norwegian_name", "treslag_")
    return df_target


def export_reference(df_ref, df_species_summary):
    # export reference data to csv
    parameters = load_parameters()
    municipality = parameters["municipality"]

    catalog = load_catalog()
    ref_trees = catalog[f"{municipality}_trees"]["reference_trees"]
    df_ref.to_csv(ref_trees["filepath_reference"], index=False, encoding="utf-8")
    df_species_summary.to_csv(
        ref_trees["filepath_species_summary"], index=False, encoding="utf-8"
    )
    return


def main():
    # set up logging
    logger = logging.getLogger(__name__)
    params = load_parameters()
    catalog = load_catalog()
    municipality = params["municipality"]
    logger.info(f"Load reference and target data for municipality: {municipality}")

    # if file not exist then create it
    if not os.path.exists(
        catalog[f"{municipality}_trees"]["reference_trees"]["filepath_reference"]
    ):
        logger.info(f"Reference data not found, creating it")
        # load reference and lookup data
        df_ref = load_reference()
        df_lookup = load_lookup()

        # CLEAN REFERENCE
        # ---------------
        df_ref = clean_reference_cols(df_ref, df_lookup)
        df_ref = clean_reference_rows(df_ref, df_lookup)

        # ENCODE SPECIES
        # --------------
        df_species_summary = calc_summary(
            df_ref, "norwegian_name", classify_other=False
        )
        filename = catalog[f"{municipality}_trees"]["reference_trees"]["filepath_plot"]
        plot_summary(
            df_species_summary,
            x="norwegian_name",
            y="Perc",
            title="Treslagsfordeling",
            xlabel="Treslag",
            ylabel="Sannsynlighet (%)",
            filename=filename,
        )
        df_ref = encode_species(df_ref)

        # EXPORT REFERENCE
        # ----------------
        export_reference(df_ref, df_species_summary)
    else:
        df_ref = pd.read_csv(
            catalog[f"{municipality}_trees"]["reference_trees"]["filepath_reference"]
        )

    # log info
    logger.info(f"Reference data shape: {df_ref.shape}")
    logger.info(f"Reference data columns: {df_ref.columns}")
    logger.info(f"Reference data head: {df_ref.head()}")
    return df_ref


if __name__ == "__main__":
    main()
