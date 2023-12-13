import json
import logging
import os
import pickle
from typing import List, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV, train_test_split

from src.config.config import load_catalog, load_parameters


def get_file_prefix(municipality, response):
    # list to string
    response_str = " ".join(response)
    response_str = response_str.replace("'", "")
    response_str = response_str.replace("[", "")
    response_str = response_str.replace("]", "")

    prefix = f"{municipality}_{response_str}_"
    return prefix


def _get_predictors(df_ref, predictors, encoding_marker) -> List:
    # if norwegian name or taxon genus in predictors get encoded cols
    if "norwegian_name" in predictors or "taxon_genus" in predictors:
        cols_encoded = [
            col for col in df_ref.columns if col.startswith(encoding_marker)
        ]

        # drop norwegian_name and/or taxon_genus from predictors
        if "norwegian_name" in predictors:
            predictors.remove("norwegian_name")
        if "taxon_genus" in predictors:
            predictors.remove("taxon_genus")

        predictors = [*predictors, *cols_encoded]
        return predictors

    else:
        return predictors


def _export_model(model, file_prefix):
    logger = logging.getLogger(__name__)
    logger.info("Export model...")
    municipality = load_parameters()["municipality"]
    catalog = load_catalog()

    # construct file path
    path = catalog[f"{municipality}_extrapolation"]["model"]["filepath_pickle"]
    filename = f"{file_prefix}_model.pkl"
    filepath = os.path.join(path, filename)

    with open(filepath, "wb") as f:
        pickle.dump(model, f)


def _export_model_params(model_params, file_prefix):
    logger = logging.getLogger(__name__)
    logger.info("Export model parameters...")
    # Save the model params to a file
    municipality = load_parameters()["municipality"]
    catalog = load_catalog()

    path = catalog[f"{municipality}_extrapolation"]["model"]["filepath_json"]
    filename = f"{file_prefix}_model_params.json"
    filepath = os.path.join(path, filename)

    with open(filepath, "w") as f:
        json.dump(model_params, f)


def _update_model_params(new_params, file_prefix):
    logger = logging.getLogger(__name__)
    logger.info("Update model parameters...")

    municipality = load_parameters()["municipality"]
    catalog = load_catalog()

    path = catalog[f"{municipality}_extrapolation"]["model"]["filepath_json"]
    filename = f"{file_prefix}_model_params.json"
    filepath = os.path.join(path, filename)

    # Load the existing parameters from the file
    with open(filepath, "r") as f:
        existing_params = json.load(f)

    # Add new parameters that don't already exist
    for key, value in new_params.items():
        if key not in existing_params:
            existing_params[key] = value

    # Write the updated parameters back to the file
    with open(filepath, "w") as f:
        json.dump(existing_params, f)


def _plot_model_performance(y_test, y_pred, dict, file_prefix):
    import matplotlib.pyplot as plt
    import seaborn as sns

    logger = logging.getLogger(__name__)
    logger.info("Plot model performance...")

    response = dict["response"]
    # list to string
    response_str = " ".join(response)
    # remove ' ' from filename
    response_str = response_str.replace("'", "")
    response_str = response_str.replace("[", "")
    response_str = response_str.replace("]", "")

    # plot results and save plot to output folder
    plt.clf()

    # Regression plot
    sns.jointplot(
        x=y_test,
        y=y_pred,
        kind="reg",
        truncate=False,
        # xlim=(0, 60), ylim=(0, 12),
        color="#427360",
        height=7,
    )
    plt.xlabel(f"actual {response_str}")
    plt.ylabel(f"predicted {response_str}")
    plt.figtext(
        0,
        -0.05,
        f"R2: {dict['r2']}    RMSE: {dict['rmse']:.2f}\
        \n{dict['model_name']}",
        ha="left",
        fontsize=10,
    )

    # save plot
    municipality = load_parameters()["municipality"]
    catalog = load_catalog()

    path = catalog[f"{municipality}_extrapolation"]["model"]["filepath_img"]
    filename = f"{file_prefix}_performance.png"
    filepath = os.path.join(path, filename)
    plt.savefig(filepath, bbox_inches="tight")


def split_data(data, model_params) -> Tuple:
    """Splits data into features and targets training and test sets.

    Args:
        data (df): Reference dataframe containing features and target.
        model_params (dict): model parameters defined in parameters.yml
    Returns:
        Split data (tpl): X_train, X_test, y_train, y_test
    """
    logger = logging.getLogger(__name__)
    logger.info("Split data into training and test sets...")

    predictors = model_params["predictors"]
    predictors = _get_predictors(
        df_ref=data, predictors=predictors, encoding_marker="SP_"
    )

    response = model_params["response"]

    # drop rows with missing values in predictors and response
    cols = [*response, *predictors]
    data = data[cols].dropna()

    X = data[predictors]
    y = data[response]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=model_params["test_size"],
        random_state=model_params["random_state"],
    )

    y_train = y_train.values.ravel()
    y_test = y_test.values.ravel()

    logger.info(f"PREDICTORS: {predictors}")
    logger.info(f"RESPONSE: {response}")
    logger.info(f"Y_train shape: {y_train.shape}")
    logger.info(f"y_test shape: {y_test.shape}")

    return response, predictors, X_train, X_test, y_train, y_test


def load_model(filepath):
    """
    Load a model from a pickle file.

    Args:
    filepath (str): path to pickle file

    Returns:
    model: model object
    """

    with open(filepath, "rb") as f:
        model = pickle.load(f)

    return model


def tune_rf(X_train, y_train, model_params, file_prefix):
    """
    Tuning random forest parameters n_estimators and max_features.
    Using grid search with 10-fold cross-validation.

    n_estimators: The number of trees in the forest.
    max_features: The number of features to consider when looking for the best split.

    Args:
        X_train (df): Training features.
        y_train (df): Training target.
        params (dict): Parameters defined in parameters/data_science.yml.

    Returns:
        best_rfmodel (obj): Best random forest model.
    """
    logger = logging.getLogger(__name__)
    logger.info("Tuning random forest parameters...")
    # Create a RadomForest regression model
    rfmodel = RandomForestRegressor(random_state=model_params["random_state"])

    # Define the parameter grid
    param_grid = {
        "n_estimators": range(1, 40),
        "max_features": [1.0, "sqrt", "log2"],
    }

    # Perform grid search
    grid_search = GridSearchCV(
        rfmodel, param_grid, cv=10, scoring="neg_mean_squared_error"
    )
    grid_search.fit(X_train, y_train)

    # Get the best model
    best_rfmodel = grid_search.best_estimator_

    # Get the best parameters
    best_params = grid_search.best_params_
    logger.info(f"Best parameters: {best_params}")

    # export best model and parameters
    _export_model(best_rfmodel, file_prefix)
    _export_model_params(best_params, file_prefix)

    return best_rfmodel


def get_model(X_train, y_train, model_params, file_prefix):
    """
    Train model using the tuned parameters stored in the model_params.json file.
    """

    logger = logging.getLogger(__name__)
    logger.info("Train model using the tuned parameters...")
    municipality = load_parameters()["municipality"]
    path = load_catalog()[f"{municipality}_extrapolation"]["model"]["filepath_json"]

    with open(path, "r") as f:
        best_params = json.load(f)

    n_estimators = best_params["n_estimators"]
    max_features = best_params["max_features"]

    # train model
    rfmodel = RandomForestRegressor(
        random_state=model_params["random_state"],
        n_estimators=n_estimators,
        max_features=max_features,
    )
    rfmodel.fit(X_train, y_train)

    # export trained model
    _export_model(rfmodel, file_prefix)
    _export_model_params(best_params, file_prefix)

    return rfmodel


def evaluate_model(model, X_test, y_test, model_params, file_prefix):
    """Evaluate model performance on test data.
    and store the results in a dictionary.

    Args:
        model (obj): Trained model.
        X_test (df): Test features.
        y_test (df): Test target.

    Returns:
        mae (float): Mean absolute error.
        mse (float): Mean squared error.
        rmse (float): Root mean squared error.
        r2 (float): R-squared.
    """
    logger = logging.getLogger(__name__)
    logger.info("Evaluate model performance on test data...")

    # Make predictions using the trained model
    y_pred = model.predict(X_test)

    # Calculate and return the RMSE
    mae = round(np.mean(np.abs(y_test - y_pred)), 2)
    mse = round(mean_squared_error(y_test, y_pred), 2)
    rmse = round(np.sqrt(mean_squared_error(y_test, y_pred)), 2)
    r2 = round(r2_score(y_test, y_pred), 2)

    dict = {
        "model_name": model_params["model_form"],
        "response": model_params["model_options"]["response"],
        "mae": mae,
        "mse": mse,
        "rmse": rmse,
        "r2": r2,
    }
    logger.info(
        f"R2: {dict['r2']} \tRMSE: {dict['rmse']:.2f}\
        \tMSE:{dict['mse']} \tMAE: {dict['mae']:.2f}\
        \n{dict['model_name']}",
    )

    _plot_model_performance(y_test, y_pred, dict, file_prefix)
    _update_model_params(dict, file_prefix)

    return dict


def predict(df_target, target_id, regressor, response, predictors):
    """Extrapolate (predict) the values to the target dataset.

    Args:
        df_target (df): Target dataset.
        model (obj): Trained model.

    Returns:
        df_target (df): Target dataset with predicted values.
    """

    logger = logging.getLogger(__name__)
    logger.info("Predicting values to target dataset...")

    # delete row if predictors contain missing values
    df = df_target.dropna(subset=predictors)
    X_target = df[predictors]

    # predict values
    y_target = regressor.predict(X_target)
    y_target = np.round(y_target, 2)
    y_target = pd.DataFrame(y_target, columns=response)

    # add predicted values to target dataset
    df_result = df.copy()
    # drop all rows starting with SP_ (encoded cols)
    df_result = df_result[df_result.columns.drop(list(df_result.filter(regex="SP_")))]
    # sort by ID
    df_result = df_result.sort_values(by=[target_id])
    df_result[response] = y_target[response]
    print(df_result.head())

    # ct.export_target(df_target)
    return df_target
