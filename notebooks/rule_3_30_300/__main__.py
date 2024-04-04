import os
import papermill as pm # execute notebooks


def main(
    input_notebook,
    output_notebook,
    municipality,
    district_numbers,
    data_path,
    fanout=True,
):
    """Run notebook for each district in municipality.

    Args:
        input_notebook (str): notebook to run
        output_notebook (str): notebook to save
        municipality (str): municipality name
        district_numbers (str): list of district numbers
        data_path (str): path to data
        fanout (bool, optional): Fanout dataset based on district number. Defaults to True.
    """    
    
    for number in district_numbers:
        print(f"Running.. district number: {number}")
        # run notebook
        pm.execute_notebook(
            input_path=input_notebook,
            output_path=output_notebook,
            parameters=dict(
                municipality=municipality,
                district_number=number,
                data_path=data_path,
                fanout=fanout,
            ),
        )
        print(f"Finished running district number: {number}")

    print("Finished running {municipality}")


if __name__ == "__main__":
    # params
    municipality = "oslo"
    district_numbers = range(30101, 30161)
    data_path = r"path/to/data"
    fanout = True

    # path current wd
    project_dir = os.getcwd()

    notebook_name = "01_split_by_district" # 02_calculate_rule_3_30_300_per_district

    input_notebook = os.path.join(
        project_dir,
        "notebooks",
        "rule_3_30_300",
        notebook_name + ".ipynb",
    )
    
    print(input_notebook)
    output_notebook = input_notebook  # overwrite cells in input notebook
    
    # run notebook for each district
    main(
        input_notebook,
        output_notebook,
        municipality,
        district_numbers,
        data_path,
        fanout,
    )
