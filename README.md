itree-support-tools
==============================

This repository provides a workflow for preparing municipal tree data for i-Tree Eco analysis and extrapolating the results to full the study area extent, using lidar-segmented tree crowns and auxiliary GIS datasets.

------------

Code is provided for the following tasks:

1. **i-Tree Eco Data Preparation:** preparing an input dataset for i-Tree Eco analysis by supplementing existing municipal tree inventories with crown geometry from the ALS data and auxiliary spatial datasets following the workflow by *Cimburova and Barton (2020).*  

2. **i-Tree Eco Extrapolation:** extrapolating the outputs from i-Tree Eco analysis to all trees in the study area following the workflow by Cimburova and Barton (2020).    

The repository is applied on the Norwegian municipalities: *Bærum, Bodø, Kristiansand* and *Oslo.* 

------------




### Project Installation and Configuration

The code is build in an ArcGIS Pro 3.1.0. conda environment with the spatial analyst license enabled. 

1. Clone the repository.
3. Open [Project structure](docs/project_structure.md) to view the structure of the project.
4. Set up your Python Environment:
    
    a. Create a new conda environment using the `environment.yml` file or clone the arcgispro-py3 environment from your ArcGIS Pro installation and install the required packages listed in the `requirements.txt` file.
    ```bash
        cd path/to/project/folder
        conda env create -f environment.yml
        conda activate project-name
    ```

    b. (Optional) Install linters using pipx 
    ```bash
        # install linters using pipx
        make install-global
        # test linters
        make codestyle
    ```

    **note:** As `pre-commit` unfortunately often gives acces-denied errors on Windows OS, I would recommend to run `make codestyle` command before you commit your changes. This command runs black, isort and ruff on all files using the configuration specified in the [pyproject.toml](pyproject.toml) file.

    c. Install as a local package 
    ```bash
        pip install .
        pip install -e . # for development
    ```
    -  installs project packages in development mode
    - creates a folder **package-name.egg-info**

    d. Configure your project. 

    - Copy template.env to  $user/.env and fill in the variables. 
    *ENSURE THAT YOU DO NOT COMMIT .ENV TO THE REPOSITORY*
    - check that your data is located in the correct folders, look at the [Project structure](docs/project_structure.md) and the [Catalog](config/catalog.yaml) for more details. 
    
    e. Define your municipality in the [parameters](config/parameters.yaml) file.

    d. Run `config.py` in the conda env to test your project config.
-------

### Workflow | i-Tree Eco Data Preparation

Detailed description of the workflow is provided in the [project note (in prep)](docs/data_preparation.md).

1. Prepare Data
    **entry point:** `prepare_data.py`
    **tasks:**
        (i) load the lidar-segmented tree crown polygons from the ALS data per neighbourhood
        (ii) load the in situ tree stems from the municipal tree inventory
        (iii) clean the in situ tree stems
            - manual municipality-specific cleaning tasks (see REF) 
            - automatic cleaning tasks:
                - set standard field design
                - translate tree species
                - ensure that each tree stem contains: stem_id, dbh, height, crown_diameter 
        (iv) group tree stem points by neighbourhood
        
2. Join the in situ tree stems with the lidar-segmented tree crowns
    **entry point:** `join_data.py`
    **tasks:** 
        (i) classify the geometrical relationship
        (ii) split lidar-segmented tree crowns that overlap with multiple tree stems
        (iii) model the crown geometry of tree stems that do not overlap with lidar-segmented trees
        (iv) quality control wether each crown polygon is assigned to a single tree stem
        (v) join the in situ tree stems with the lidar-segmented tree crowns
        
    **Geometrical Relations:**
    - **Case 1:** one polygon contains one point (1:1), simple join.  
    - **Case 2:** one polygon contains more than one point (1:n), split crown with voronoi tesselation.
    - **Case 3:** a point is not overlapped by any polygon (0:1), model tree crown using oslo formula.
    - **Case 4:** a polygon does not contain any point (1:0), not used to train i-tree eco/dataset for extrapolation.

3. Compute tree attributes and auxillary attributes
    
    **entry point:** `compute_attributes.py`
    **tasks:** 
        (i) compute tree crown attributes (all trees in thes study area)
            - overlay attributes (pollution zone, neighbourhood code)
            - crown_id (based on neighbourhood code and objectid)
            - tree height, crown area 
        (ii) compute tree stem attributes (in-situ trees)
            - overlay attributes (e.g. pollution zone, neighbourhood code, land use) 
            - tree attributes (e.g. dbh, height, crown diameter)
            - join crown attributes (e.g. crown_id, crown area, crown volume, crown shape)
            - building related attributes (e.g. building distance, building direction)
            - crown condition (e.g. crown light exposure)
        
    **IMPORTANT NOTES**: do not run building related attr. and crown condition attr. within pipeline. Run them separatly and cosely check the results. 

    **STEP 3 NEEDS CLEANING, BUILDING CROWN CONDITION SUPER SLOW (e.g. +12h runtime)**
----------------
### Workflow | i-Tree Eco Extrapolation

Detailed description of the workflow is provided in the [project note](docs/extrapolation.md). 




----------------

### References 
- Cimburova, Z., & Barton, D. N. (2020). The potential of geospatial analysis and Bayesian networks to enable i-Tree Eco assessment of existing tree inventories. Urban Forestry & Urban Greening, 55, 126801. https://doi.org/10.1016/j.ufug.2020.126801


### Acknowledgments

*This repository is part of the project:*

**TREKRONER Prosjektet** | Trærs betydning for klimatilpasning, karbonbinding, økosystemtjenester og biologisk mangfold. 

This repository uses code adapted fromt the repository [i-Tree-Eco](https://github.com/zofie-cimburova/i-Tree-Eco) by Cimburova, Z. 2022, this repository is licensed under the GNU General Public License (GPL).