import logging
import os

import src.utils.decorators as dec
from extrapolation import clean_reference, clean_target, regressor
from src.config.config import load_catalog, load_parameters
from src.config.logger import setup_logging


@dec.timer
def prepare_data():
    # Clean data
    # ---------------------------
    # fill missing values for dbh based on height or crown_diam
    # encode categorical variables
    municipality = load_parameters()["municipality"]
    params = load_parameters()
    ref_id = params[municipality]["ref_id"]
    target_id = params[municipality]["target_id"]
    col_species = params[municipality]["col_species"]

    df_ref = clean_reference.main(col_id=ref_id, col_species=col_species)
    df_target = clean_target.main(col_id=target_id, col_species=col_species)

    # Split data
    # ---------------------------
    # model that contains all variables
    model_params = load_parameters()["rf_total_cap"]

    response, predictors, X_train, X_test, y_train, y_test = regressor.split_data(
        df_ref, model_params=model_params["model_options"]
    )

    return response, predictors, X_train, X_test, y_train, y_test, df_target


@dec.timer
def totben_cap(response, predictors, X_train, X_test, y_train, y_test, df_target):
    """
    Predict the total annual benefits (Nkr/år) of trees
    in the municipalities building zone.
    """

    municipality = load_parameters()["municipality"]
    catalog = load_catalog()

    # load model parameters
    model_params = load_parameters()["rf_total_cap"]
    target_id = load_parameters()[municipality]["target_id"]
    response = model_params["model_options"]["response"]

    file_prefix = regressor.get_file_prefix(municipality, response)
    print(file_prefix)

    path = catalog[f"{municipality}_extrapolation"]["model"]["filepath_pickle"]
    filename = f"{file_prefix}_model.pkl"
    model_filepath = os.path.join(path, filename)

    # if model exist then load it, else train new model
    if os.path.exists(model_filepath):
        rfmodel = regressor.load_model(model_filepath)
    else:
        rfmodel = regressor.tune_rf(
            X_train,
            y_train,
            model_params=model_params["model_options"],
            file_prefix=file_prefix,
        )

    # evaluate model
    regressor.evaluate_model(
        rfmodel, X_test, y_test, model_params=model_params, file_prefix=file_prefix
    )

    # predict target data
    regressor.predict(
        df_target=df_target,
        target_id=target_id,
        regressor=rfmodel,
        response=response,
        predictors=predictors,
    )
    return


@dec.timer
def individual_es(X_train, X_test, y_train, y_test, response, predictors, df_target):
    """Predict the individual ecosystem services of trees
    in the municipalities building zone."""

    params = load_parameters()
    catalog = load_catalog()

    model_type = "rf_individual_es"


if __name__ == "__main__":
    # set up logging
    setup_logging()
    logger = logging.getLogger(__name__)
    response, predictors, X_train, X_test, y_train, y_test, df_target = prepare_data()
    totben_cap(response, predictors, X_train, X_test, y_train, y_test, df_target)
