# nodes.py
import logging

import pandas as pd

from src.config.config import load_catalog, load_parameters


def load_reference(reference_municipality="oslo"):
    """Load reference data."""

    # set up logging
    logger = logging.getLogger(__name__)
    catalog = load_catalog()
    parameters = load_parameters()
    municipality = parameters["municipality"]
    logger.info(f"Loading reference data for municipality: {municipality}")

    # concat string
    if reference_municipality == "oslo":
        reference_str = f"reference_{reference_municipality}"
    else:
        reference_str = "reference_municipality"

    reference_excel = catalog[reference_str]["filepath"]
    reference_sheet = catalog[reference_str]["sheet_names"][1]
    logger.info(f"Loading reference data from file: {reference_excel}")

    # Load reference data into df
    workbook = pd.ExcelFile(reference_excel)
    sheet_names = workbook.sheet_names
    logger.info(f"workbook sheet names: {sheet_names}")

    df_reference = pd.read_excel(reference_excel, sheet_name=reference_sheet)

    # Load metadata into df
    df_metadata = pd.read_excel(reference_excel, sheet_name="metadata")
    df_metadata = df_metadata[["reference_colnames", "python_colnames", "dtype"]]

    # Load species list
    df_species = pd.read_excel(reference_excel, sheet_name="unique_species")
    species_bins = df_species["scientific_name"].tolist()

    # Log Reference Data info
    logger.info(f"Reference data ({df_reference.shape}): \n{df_reference.head()}")
    logger.info(f"Metadata {df_metadata.shape}: \n{df_metadata.head()}")
    logger.info(f"species {df_species.shape}: \n{species_bins[:5]}")

    return df_reference, df_metadata, df_species, species_bins


def load_target():
    """Load target data"""

    # set up logging
    logger = logging.getLogger(__name__)
    catalog = load_catalog()
    parameters = load_parameters()
    municipality = parameters["municipality"]
    logger.info(f"Loading target data for municipality: {municipality}")

    target_excel = catalog["target_municipality"]["filepath"]
    target_sheet = catalog["target_municipality"]["sheet_names"][1]
    logger.info(f"Loading target data from sheet: {target_sheet}")

    # load csv into df target_oslo.csv
    df_target = pd.read_excel(target_excel, sheet_name=target_sheet)

    # log target data info
    logger.info(f"Target data ({df_target.shape}): /n{df_target.head()}")

    # count of itree_spec == 0 (set null to 0 covert to int first)
    df_target["itree_spec"] = df_target["itree_spec"].fillna(0)
    df_target["itree_spec"] = df_target["itree_spec"].astype(int)
    count = df_target["itree_spec"].value_counts()
    logger.info(f"itree_spec == 0: {count[0]}")
    logger.info(f"itree_spec == 1 (removed from target): {count[1]}")

    # remove all rows in column itree_spec where itree_spec = 0
    df_target = df_target[df_target["itree_spec"] == 0]
    logger.info(f"Target data loaded into df_target: {df_target.shape}")

    return df_target


def load_output():
    """Load output data"""

    # set up logging
    logger = logging.getLogger(__name__)
    catalog = load_catalog()
    parameters = load_parameters()
    municipality = parameters["municipality"]
    logger.info(f"Loading output data for municipality: {municipality}")

    # output
    output_extrapolation = catalog["extrapolated_values"]["filepath"]
    logger.info(f"Loading output data: {output_extrapolation}")

    return output_extrapolation


def column_cleaner(df, df_metadata):
    # trim and rename columns using metadata
    col_name_mapping = dict(
        zip(df_metadata["reference_colnames"], df_metadata["python_colnames"])
    )
    df.columns = df.columns.str.strip()
    df.rename(columns=col_name_mapping, inplace=True)
    df.columns = df.columns.str.strip()

    # update column dtypes using metadata
    dtype_mapping = dict(zip(df_metadata["python_colnames"], df_metadata["dtype"]))

    # remove all values from dtype_mapping if they are not in df.columns
    dtype_mapping = {
        key: dtype_mapping[key] for key in dtype_mapping.keys() if key in df.columns
    }

    # convert column dtypes using dtype_mapping
    for key in dtype_mapping.keys():
        # print(f"column: {key}\t current dtype: {df[key].dtypes} \ttarget dtype: {dtype_mapping[key]}")
        # if the current dtype is not the target dtype, convert the column
        if df[key].dtypes != dtype_mapping[key]:
            try:
                if dtype_mapping[key] == "int":
                    df[key] = df[key].astype(int)
                    print(f"column: {key} converted to {df[key].dtypes}")
                elif dtype_mapping[key] == "float64":
                    df[key] = df[key].astype(float)
                    print(f"column: {key} converted to {df[key].dtypes}")
                elif dtype_mapping[key] == "object":
                    df.astype({key: "object"}).dtypes
                    print(f"column: {key} converted to {df[key].dtypes}")
            except ValueError:
                print(
                    f"column: {key} ({df[key].dtypes}) could not be converted to {dtype_mapping[key]}"
                )
                pass
        else:
            print(
                f"column: {key} ({df[key].dtypes}) has already dtype: {dtype_mapping[key]}"
            )
            pass

    return df


def prepare_reference(df_reference, df_metadata, df_species, species_bins):
    """
    Clean reference dataset for training and testing.
    - remove missing values
    - remove negative values
    """

    # set up logging
    logger = logging.getLogger(__name__)
    df = df_reference.copy()

    # remove all rows in column itree_spec where itree_spec = 0
    df = df[df["itree_spec"] != 0]
    logger.info(f"Remove null values: {df.isnull().sum()}")

    df = column_cleaner(df, df_metadata)
    logger.info(f"Reference data cols: {df.columns}")

    # remove all rows with missing values in columns: crown_area, height_total_tree,scientific_name, pollution_zone
    logger.info(f"Null values in crown_area: {df['crown_area'].isnull().sum()}")
    logger.info(
        f"Null values in height_total_tree: {df['height_total_tree'].isnull().sum()}"
    )
    logger.info(
        f"Null values in scientific_name: {df['scientific_name'].isnull().sum()}"
    )
    logger.info(f"Null values in pollution_zone: {df['pollution_zone'].isnull().sum()}")

    df = df.dropna(
        subset=["crown_area", "height_total_tree", "scientific_name", "pollution_zone"]
    )

    # Set negative values to 0 for cols and round to 3 decimals
    # crown_area height_total_tree
    # co2_storage_kg co2_seq_kg_yr runoff_m3_yr
    # pollution_g_yr pollution_co pollution_o3 pollution_no2 pollution_so2 pollution_pm25 totben_cap

    # TODO move to catalog
    cols = [
        "crown_area",
        "height_total_tree",
        "co2_storage_kg",
        "co2_seq_kg_yr",
        "runoff_m3_yr",
        "pollution_g_yr",
        "pollution_co",
        "pollution_o3",
        "pollution_no2",
        "pollution_so2",
        "pollution_pm25",
        "totben_cap",
    ]

    # set negative values to 0
    df[cols] = df[cols].clip(lower=0)
    # round to 3 decimals
    df[cols] = df[cols].round(3)
    logger.info(f"DF cleaned for null values and clipped negative values: {df.shape}")

    return df


def pipeline(reference_municipality="oslo"):
    # load reference
    df_reference, df_metadata, df_species, species_bins = load_reference(
        reference_municipality
    )

    # load target
    df_target = load_target()

    # load output
    output_extrapolation = load_output()

    # Prepare the data
    prepared_data = prepare_reference(
        df_reference, df_metadata, df_species, species_bins
    )

    return


def train_model(prepared_data):
    # Train a linear regression model

    # Return the trained model
    return model


def score_model(trained_model, input_data):
    # Make predictions using the trained model
    predicted_scores = np.polyval(trained_model, input_data[:, 0])

    # Return the predicted scores
    return predicted_scores


def evaluate_model(predicted_scores, actual_scores):
    # Calculate and return the RMSE
    rmse = np.sqrt(np.mean((predicted_scores - actual_scores) ** 2))
    return rmse


def predict(prepared_data, trained_model):
    # Return the model predictions
    return trained_model.predict(prepared_data)
