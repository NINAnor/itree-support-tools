import logging
import os
import src.utils.decorators as dec
from extrapolation import clean_reference, clean_target, model
from src.config.logger import setup_logging
from src.config.config import load_catalog, load_parameters


@dec.timer
def main():
    """Run main script."""

    # Prepare data
    # ---------------------------
    # clean data
    # fill missing values for dbh based on height or crown_diam
    # encode categorical variables
    params = load_parameters()
    catalog = load_catalog()

    df_ref = clean_reference.main(col_id="tree_id", col_species="taxon_genus")
    # df_target = clean_target.main(col_id="OBJECTID", col_species="taxon_genus")

    # Split data
    # ---------------------------
    model_type = "rf_total_cap"
    model_params = load_parameters()["rf_total_cap"]

    X_train, X_test, y_train, y_test = model.split_data(
        df_ref, params=model_params["model_options"]
    )
    y_train = y_train.values.ravel()
    y_test = y_test.values.ravel()

    # if model (pickle) does not exist then train otherwise load
    path_model = catalog[f"{params['municipality']}_extrapolation"]["model"][
        "filepath_pickle"
    ]
    if not os.path.exists(path_model):
        rfmodel = model.tune_rf(X_train, y_train, params=model_params["model_options"])
        model.evaluate_model(rfmodel, X_test, y_test, params=model_params)
    else:
        rfmodel = model.load_model()
        # rfmodel = model.get_model(X_train, y_train, model_params)
        model.evaluate_model(rfmodel, X_test, y_test, params=model_params)

    return


if __name__ == "__main__":
    # set up logging
    setup_logging()
    logger = logging.getLogger(__name__)
    main()
