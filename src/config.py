"""Project configuration"""

import os
from pathlib import Path

from dotenv import load_dotenv

from src.utils.yaml_utils import yaml_load

# --------------------------------------------------------------------------- #
# Load secure variables from .env file
# --------------------------------------------------------------------------- #

# for .env file in USER directory
# user_dir = C:\\USERS\\<<firstname.lastname>>
user_dir = os.path.join(os.path.expanduser("~"))
dotenv_path = os.path.join(user_dir, "trekroner.env")
load_dotenv(dotenv_path)

# path to yaml project configuration file
project_root = Path(__file__).parents[1]
config_file = os.path.join(project_root, "config/config.yaml")


# --------------------------------------------------------------------------- #
def load_catalog():
    """Load catalog from yaml file.

    Returns
    -------
    dict: catalog
    """
    catalog = os.path.join(project_root, "config/catalog.yaml")
    with open(catalog, "r") as f:
        catalog = yaml_load(f)

    # replace municipality variable with correct municipality
    municipality = load_parameters()["municipality"]

    for key, value in catalog.items():
        catalog[key]["filepath"] = value["filepath"].replace(
            "<<municipality>>", municipality
        )

    return catalog


def load_parameters():
    """Load parameters from yaml file

    Returns
    -------
    dict: parameters
    """
    parameters = os.path.join(project_root, "config/parameters.yaml")
    with open("../config/parameters.yaml", "r") as f:
        parameters = yaml_load(f)
    return parameters


# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    # load catalog
    print("Loading catalog...")
    catalog = load_catalog()
    parameters = load_parameters()
    print(catalog)
