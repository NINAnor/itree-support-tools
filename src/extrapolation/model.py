import logging
import os
from typing import Dict, Tuple, List
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import cross_val_score
from sklearn.metrics import mean_squared_error, r2_score
import numpy as np

from src.config.config import load_catalog, load_parameters

params = load_parameters()
predictors = params["rf_total_cap"]["model_options"]["predictors"]
response = params["rf_total_cap"]["model_options"]["response"]


def load_model():
    import pickle
    import os

    # Load the model from a file
    params = load_parameters()
    municipality = params["municipality"]
    path = load_catalog()[f"{municipality}_extrapolation"]["model"]["filepath_pickle"]
    with open(path, "rb") as f:
        model = pickle.load(f)

    return model


def get_predictors(df_ref, predictors, encoding_marker) -> List:
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


def split_data(data, params) -> Tuple:
    """Splits data into features and targets training and test sets.

    Args:
        data (df): Reference dataframe containing features and target.
        parameters (dict): Parameters defined in parameters/data_science.yml.
    Returns:
        Split data (tpl): X_train, X_test, y_train, y_test
    """
    logger = logging.getLogger(__name__)

    predictors = params["predictors"]
    predictors = get_predictors(
        df_ref=data, predictors=predictors, encoding_marker="SP_"
    )

    response = params["response"]

    cols = [*response, *predictors]
    # drop rows with missing values in predictors and response
    data = data[cols].dropna()

    X = data[predictors]
    print(X.head())
    y = data[response]
    print(y.head())

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=params["test_size"], random_state=params["random_state"]
    )

    logger.info(f"PREDICTORS: {predictors}")
    logger.info(f"RESPONSE: {response}")
    logger.info(f"Y_train shape: {y_train.shape}")
    logger.info(f"y_test shape: {y_test.shape}")

    return X_train, X_test, y_train, y_test


from sklearn.model_selection import GridSearchCV


def tune_rf(X_train, y_train, params):
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
    rfmodel = RandomForestRegressor(random_state=params["random_state"])

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
    export_model(best_rfmodel, "best_rfmodel")
    export_model_params(best_params, "best_rfmodel")

    return best_rfmodel


def get_model(X_train, y_train, params):
    """
    Train model using the tuned parameters.
    """
    import json
    import os

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
        random_state=params["model_options"]["random_state"],
        n_estimators=n_estimators,
        max_features=max_features,
    )
    rfmodel.fit(X_train, y_train)

    # export trained model
    export_model(rfmodel)
    export_model_params(best_params)

    return rfmodel


def export_model(model):
    import pickle
    import os

    # Save the model to a file
    params = load_parameters()
    municipality = params["municipality"]
    catalog = load_catalog()[f"{municipality}_extrapolation"]["model"]

    with open(catalog["filepath_pickle"], "wb") as f:
        pickle.dump(model, f)


def export_model_params(params):
    import json
    import os

    # Save the model params to a file
    municipality = load_parameters()["municipality"]
    path = load_catalog()[f"{municipality}_extrapolation"]["model"]["filepath_json"]
    with open(path, "w") as f:
        json.dump(params, f)


def update_model_params(new_params):
    import json
    import os

    # Load the existing parameters
    municipality = load_parameters()["municipality"]
    path = load_catalog()[f"{municipality}_extrapolation"]["model"]["filepath_json"]

    # Load the existing parameters from the file
    with open(path, "r") as f:
        existing_params = json.load(f)

    # Add new parameters that don't already exist
    for key, value in new_params.items():
        if key not in existing_params:
            existing_params[key] = value

    # Write the updated parameters back to the file
    with open(path, "w") as f:
        json.dump(existing_params, f)


def evaluate_model(model, X_test, y_test, params):
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
    mae = np.mean(np.abs(y_test - y_pred))
    mse = mean_squared_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)

    dict = {
        "model_name": params["model_form"],
        "response": params["model_options"]["response"],
        "mae": mae,
        "mse": mse,
        "rmse": rmse,
        "r2": r2,
    }

    update_model_params(dict)
    plot_model_performance(y_test, y_pred, dict)

    return dict


def plot_model_performance(y_test, y_pred, dict):
    import matplotlib.pyplot as plt
    import seaborn as sns

    response = dict["response"]
    # list to string
    response_str = " ".join(response)
    # remove ' ' from filename
    response_str = response_str.replace("'", "")
    response_str = response_str.replace("[", "")
    response_str = response_str.replace("]", "")

    # plot results and save plot to output folder
    plt.clf()  # clear figure

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
        f"R2: {dict['r2']}   RMSE: {dict['rmse']:.2f}   MAE: {dict['mae']:.2f} \n {dict['model_name']}",
        ha="left",
        fontsize=8,
    )

    # save plot
    municipality = load_parameters()["municipality"]
    catalog = load_catalog()["oslo_extrapolation"]["model"]["filepath_img"]
    file_name = f"{municipality}_{response_str}_performance.png"
    path = os.path.join(catalog, file_name)

    plt.savefig(path, bbox_inches="tight")


def predict(prepared_data, trained_model):
    # Return the model predictions
    return trained_model.predict(prepared_data)


def main():
    params = load_parameters()

    municipality = params["municipality"]

    # if kristiansand use lr_total_cap else rf_total_cap
    if municipality == "kristiansand":
        model_params = params["lr_total_cap"]["model_options"]
    else:
        model_params = params["rf_total_cap"]["model_options"]
