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
    df_metadata = df_metadata[["reference_data_names", "python_colnames", "dtype"]]

    # Load species list
    df_species = pd.read_excel(reference_excel, sheet_name="unique_species")
    species_bins = df_species["species"].tolist()

    # Log Reference Data info
    logger.info(f"Reference data ({df_reference.shape}): /n{df_reference.head()}")
    logger.info(f"Metadata ({df_metadata.shape}): /n{df_metadata.head()}")
    logger.info(f"species ({df_species.shape}): /n{species_bins}")

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
        zip(df_metadata["urban-treeDetection_colnames"], df_metadata["python_colnames"])
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

    df = df_reference.copy()
    df = column_cleaner(df, df_metadata)
    logger.info(f"Reference data cols: {df.columns}")
    logger.info(f"Remove null values: {df.isnull().sum()}")

    # Remove missing values
    df = df.dropna()

    # Remove negative values

    # Return the prepared data

    return


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
    model = np.polyfit(prepared_data[:, 0], prepared_data[:, 1], 1)

    # Return the trained model
    return model


def score_model(trained_model, input_data):
    # Make predictions using the trained model
    predicted_scores = np.polyval(trained_model, input_data[:, 0])

    # Return the predicted scores
    return predicted_scores
