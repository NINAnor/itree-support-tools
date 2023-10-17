py-windows-template
==============================

This is a template for a python project on Windows using Conda and VS Code. 

### Project Installation and Configuration

The code is build in an ArcGIS Pro 3.1.0. conda environment with spatial analyst licensed enabled. 

1. Clone the repository.
3. Open [Project structure](docs/project_structure.md) to view the structure of this template.
4. Set up your Python Environment:
    
    a. Create a new conda environment using the `environment.yml` file:
    ```bash
        cd path/to/project/folder
        conda env create -f environment.yml
        conda activate project-name
    ```

    b. Install linters using pipx 
    ```bash
        # install linters using pipx
        make install-global
        # test linters
        make codestyle
    ```

    **note:** As `pre-commit` unfortunately gives acces-denied errors on Windows OS, I would recommend to run `make codestyle` command before you commit your changes. This command runs black, isort and ruff on all files.

    c. Install your local package 
    ```bash
        pip install -e .
    ```
    -  installs project packages in development mode
    - creates a folder **package-name.egg-info**

    d. Run `config.py` in the conda env to test your project config.
-------

### Workflow







### References
- *text here*
- *text here*

### Citation
*text here*

### Acknowledgments

*This repository is part of the project:*

** xxxx Project** | Long name project.
