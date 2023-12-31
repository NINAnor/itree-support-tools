import logging
import os

import src.utils.decorators as dec
from src.config.config import load_catalog, load_parameters
from src.config.logger import setup_logging
from src.extrapolation import clean_reference, clean_target, export_results, regressor


@dec.timer
def prepare_data():
    # Clean data
    # ---------------------------
    # fill missing values for dbh based on height or crown_diam
    # encode categorical variables
    municipality = load_parameters()["municipality"]

    if municipality == "baerum":
        params = load_parameters()
        ref_id = params["oslo"]["ref_id"]
        target_id = params["baerum"]["target_id"]
        col_species = params["baerum"]["col_species"]

        df_ref = clean_reference.main(col_id=ref_id, col_species=col_species)
        df_target = clean_target.main(col_id=target_id, col_species=col_species)

        return df_ref, df_target

    else:
        params = load_parameters()
        ref_id = params[municipality]["ref_id"]
        target_id = params[municipality]["target_id"]
        col_species = params[municipality]["col_species"]

        df_ref = clean_reference.main(col_id=ref_id, col_species=col_species)
        df_target = clean_target.main(col_id=target_id, col_species=col_species)

        return df_ref, df_target


@dec.timer
def totben_cap(df_ref, df_target):
    """
    Predict the total annual benefits (Nkr/år) of trees
    in the municipalities building zone.
    """
    municipality = load_parameters()["municipality"]
    catalog = load_catalog()

    # load model parameters
    model_params = load_parameters()["rf_total_cap"]
    target_id = load_parameters()[municipality]["target_id"]

    if municipality == "baerum":
        municipality = "oslo"

    response = model_params["model_options"]["response"]
    predictors = model_params["model_options"]["predictors"]

    # Split data
    # ---------------------------
    # model that contains all variables
    predictors, X_train, X_test, y_train, y_test = regressor.split_data(
        data=df_ref,
        model_params=model_params["model_options"],
        response=response,
        predictors=predictors,
    )

    file_prefix = regressor.get_file_prefix(municipality, response)
    print(file_prefix)

    path = catalog[f"{municipality}_extrapolation"]["model"]["filepath_pickle"]
    filename = f"{file_prefix}_model.pkl"
    model_filepath = os.path.join(path, filename)

    # Train model
    # -----------
    # if model exist then load it, else train new model
    if os.path.exists(model_filepath):
        regression_model = regressor.load_model(model_filepath)
    else:
        if municipality == "kristiansand":
            regression_model = regressor.linear_regression(
                X_train, y_train, file_prefix
            )
        else:
            regression_model = regressor.tune_rf(
                X_train,
                y_train,
                model_params=model_params["model_options"],
                file_prefix=file_prefix,
            )

    # Evaluate model
    # --------------
    regressor.evaluate_model(
        regression_model,
        response,
        X_test,
        y_test,
        model_params=model_params,
        file_prefix=file_prefix,
    )

    # Predict
    # -------
    regressor.predict(
        df_target=df_target,
        target_id=target_id,
        regressor=regression_model,
        response=response,
        predictors=predictors,
        file_prefix=file_prefix,
    )
    return


@dec.timer
def individual_es(df_ref, df_target):
    """Predict the individual ecosystem services of trees
    in the municipalities building zone."""

    municipality = load_parameters()["municipality"]
    catalog = load_catalog()

    # load model parameters
    model_params = load_parameters()["rf_individual_es"]
    target_id = load_parameters()[municipality]["target_id"]

    if municipality == "baerum":
        municipality = "oslo"

    predictors = model_params["model_options"]["predictors"]
    lst_response_variables = model_params["model_options"]["response"]
    if isinstance(lst_response_variables, str):
        lst_response_variables = [lst_response_variables]

    if municipality == "bodo":
        # drop "pollution_no2", "pollution_pm25", "pollution_so2"
        lst_response_variables = [
            x
            for x in lst_response_variables
            if x not in ["pollution_no2", "pollution_pm25", "pollution_so2"]
        ]

    # loop over response variables, model and predict
    for y_var in lst_response_variables:
        # ensure y_var is a list of (one) string
        if isinstance(y_var, str):
            y_var = [y_var]

        # Split data
        # ---------------------------
        # model that contains all variables
        predictors, X_train, X_test, y_train, y_test = regressor.split_data(
            data=df_ref,
            model_params=model_params["model_options"],
            response=y_var,
            predictors=predictors,
        )

        file_prefix = regressor.get_file_prefix(municipality, y_var)

        path = catalog[f"{municipality}_extrapolation"]["model"]["filepath_pickle"]
        filename = f"{file_prefix}_model.pkl"
        model_filepath = os.path.join(path, filename)

        # Train model
        # -----------
        # if model exist then load it, else train new model
        if os.path.exists(model_filepath):
            regression_model = regressor.load_model(model_filepath)
        else:
            if municipality == "kristiansand":
                regression_model = regressor.linear_regression(
                    X_train, y_train, file_prefix
                )
            else:
                regression_model = regressor.tune_rf(
                    X_train,
                    y_train,
                    model_params=model_params["model_options"],
                    file_prefix=file_prefix,
                )

        # Evaluate model
        # --------------
        regressor.evaluate_model(
            regression_model,
            y_var,
            X_test,
            y_test,
            model_params=model_params,
            file_prefix=file_prefix,
        )

        # Predict
        # -------
        regressor.predict(
            df_target=df_target,
            target_id=target_id,
            regressor=regression_model,
            response=y_var,
            predictors=predictors,
            file_prefix=file_prefix,
        )


@dec.timer
def carbon_es(df_ref, df_target):
    """Predict the individual ecosystem services of trees
    in the municipalities building zone."""

    municipality = load_parameters()["municipality"]
    catalog = load_catalog()

    # load model parameters
    model_params = load_parameters()["rf_carbon_es"]
    target_id = load_parameters()[municipality]["target_id"]

    if municipality == "baerum":
        municipality = "oslo"

    predictors = model_params["model_options"]["predictors"]
    lst_response_variables = model_params["model_options"]["response"]
    if isinstance(lst_response_variables, str):
        lst_response_variables = [lst_response_variables]

    # loop over response variables, model and predict
    for y_var in lst_response_variables:
        # ensure y_var is a list of (one) string
        if isinstance(y_var, str):
            y_var = [y_var]

        # Split data
        # ---------------------------
        # model that contains all variables
        predictors, X_train, X_test, y_train, y_test = regressor.split_data(
            data=df_ref,
            model_params=model_params["model_options"],
            response=y_var,
            predictors=predictors,
        )

        file_prefix = regressor.get_file_prefix(municipality, y_var)

        path = catalog[f"{municipality}_extrapolation"]["model"]["filepath_pickle"]
        filename = f"{file_prefix}_model.pkl"
        model_filepath = os.path.join(path, filename)

        # Train model
        # -----------
        # if model exist then load it, else train new model
        if os.path.exists(model_filepath):
            regression_model = regressor.load_model(model_filepath)
        else:
            if municipality == "kristiansand":
                regression_model = regressor.linear_regression(
                    X_train, y_train, file_prefix
                )
            else:
                regression_model = regressor.tune_rf(
                    X_train,
                    y_train,
                    model_params=model_params["model_options"],
                    file_prefix=file_prefix,
                )

        # Evaluate model
        # --------------
        regressor.evaluate_model(
            regression_model,
            y_var,
            X_test,
            y_test,
            model_params=model_params,
            file_prefix=file_prefix,
        )

        # Predict
        # -------
        regressor.predict(
            df_target=df_target,
            target_id=target_id,
            regressor=regression_model,
            response=y_var,
            predictors=predictors,
            file_prefix=file_prefix,
        )


def export():
    municipality = load_parameters()["municipality"]
    target_id = load_parameters()[municipality]["target_id"]
    col_species = load_parameters()[municipality]["col_species"]
    export_results.merge_csv(col_id=target_id, col_species=col_species)
    # clean_results.merge_geojson(col_id=target_id)


def summary_stat():
    parameters = load_parameters()
    municipality = parameters["municipality"]
    catalog = load_catalog()
    csv_folder = catalog[f"{municipality}_extrapolation"]["output"]["filepath_csv"]
    input_file = os.path.join(csv_folder, f"{municipality}_extrapolation_results.csv")

    municipality = load_parameters()["municipality"]
    target_id = load_parameters()[municipality]["target_id"]
    col_species = load_parameters()[municipality]["col_species"]
    export_results.create_summary(input_file, csv_folder, col_species)
    return


if __name__ == "__main__":
    # set up logging
    setup_logging()
    logger = logging.getLogger(__name__)

    # df_ref, df_target = prepare_data()
    # totben_cap(df_ref, df_target)
    # individual_es(df_ref, df_target)
    # carbon_es(df_ref, df_target)
    # export()
    summary_stat()
