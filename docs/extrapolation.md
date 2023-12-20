# Extrapolation | regression models to predict i-Tree Eco values

We use regression models to predict the i-Tree Eco values for each tree in the study area (building zone extent of the municipality.)


The study by Barton, D. and Venter, Z. (2022) and the study by Cimburova and Barton, D. (2020) uses a Bayesian network to predict the i-Tree Eco values for trees located within Oslo's building zone. 

They find that tree height, crown area and air pollution variables are most important for predicting carbon storage, carbon sequestration, air pollution reduction and water runoff reduction (Barton, D. and Venter, Z. 2022). To predict the total benefits of trees, Cimburova and Barton (2020) add tree species and diameter at breast height (DBH) as predictors to the Bayesian network.

In this study, we use regression models instead of Bayesian networks to predict the i-Tree Eco values for each tree in the study area. 
This enables us to simplify and automate the workflow and to use the same workflow for each tree crown municipality.
The following i-Tree Eco Ecosystem Service values are predicted:
- carbon storage
- carbon sequestration
- air pollution reduction
- water runoff reduction
- total benefits

For Oslo also indiviual air pollution reduction values are predicted: NO2, PM2.5 and 03. 

For the total benefits we use the following predictors: tree species, dbh, tree height, crown area, crown diameter and pollution zone. 
For the individual ecosystem services we test different predictor combinations.
- tree height, crown area and pollution zone
- tree height, crown area, pollution zone and dbh 
- tree height, crown area, pollution zone, dbh and tree species 

Workflow:
1. Data Preparation

We use the in situ municipal tree inventory with i-Tree Eco values as reference data. First, we ensure that each in situ tree stem contains the following predictor variables: species, dbh, height, crown_area, crown_diameter and pollution zone. 
If DBH or height values are missing we fill them using the following formulas:
    Equation 1: dbh = 4.04 * height^0.82
    Equation 2: dbh = (crown_diam^2.63)/(3.48^2.63)
    Equation 3: height = (dbh*1.22)/(4.04^1.22)

If other predictor values are missing we fill them using the median value of the respective variable. We use the median value instead of the mean value as the median is less sensitive to outliers. Tree species are encoded as a categorical variable. Bærum municipality does not have sufficient DBH and species information, in addition is the data skewed to Large Oaks as the field data was not obtained specifically for i-Tree Eco modelling but for identifyting hollow oaks. We assume that the tree species distribution is similar to Oslo and use Oslo's municipal tree inventory as reference dataset for Bærum.

2. Regressor selection: Random Forest vs Linear Regression

We use a Random Forest Regressor if the reference datast contains more than 1000 trees (Bodø and Oslo), otherwise we use a Linear Regression model (Kristiansand). A Random Forest Regressor is a non-parametric model that can capture non-linear relationships between the predictor and response variables. A Random Forest (REF) builds multiple decision trees, with each tree being trained on a random subset of the training data. The Random Forest Regressor then averages the predictions of each tree to make a final prediction (REF). The number of trees in the fores (N estimators) and the maximum features considered for splitting a node (Max features) are parameters that can be tuned. Random Forest models can be prone to overfitting, therefore it is recommended to tune the parameters of the model and to test the model on unseen data (REF). 

We split our reference dataset into a training (80%) and test (20%) dataset. A grid search is implemented to tune the parameters Max features and N estimators. Within this grid-search a 10-fold cross-validation is used to evaluate the performance of each model. The optimal model, i.e. the model with the highest R2 score, is then evaluated against an external test dataset. 

A linear regression model is a parametric model that assumes a linear relationship between the predictor and response variables (REF). A linear regression model is better suited for small datasets as it is less prone to overfitting than a Random Forest Regressor (REF). The linear models on this study are trained on the training (80%) dataset and evaluated against the test (20%) dataset.

3. Predict i-Tree Eco values for each tree crown

The target dataset consists of the tree crowns segmented from the lidar point cloud. The target dataset contains the following predictor variables: tree height, crown area, crown diameter and pollution zone. Tree species is predicted from the tree species distribution of the reference dataset, DBH is predicted using tree height (Eq 1.). Other missing values are filled using the median value of the respective variable. 
Thereafter categorical variables are encoded and the optimal model is used to predict the i-Tree Eco values for each tree crown. 


Model Peformance 

Oslo:

Table 1 shows the model performance of the Random Forest Regressor using different predictor combinations. The model performance is evaluated using the R2 score and the root mean squared error (RMSE). The R2 score is a measure of how well the model fits the data. The R2 score is between 0 and 1, with 1 indicating a perfect fit (REF). The RMSE is a measure of how well the model predicts the data. The RMSE is between 0 and infinity, with 0 indicating a perfect prediction (REF). 

Table 1: Model performance of the Random Forest Regressor using different predictor combinations.

For the indiviual ecosystem models the best R2 and RMSE values are obtained with all predictor variables. The model performance slightly decreases when using only tree height, crown area and pollution zone and DBH as predictor variables. The model performance decreases further when using only tree height, crown area and pollution zone for the carbon storage and carbon sequestration models. 

For the water runoff redcution and pollution reduction models the model performance we select the model with height, crown area and pollution zone as predictor variables. The model performance is slighlty lower than the model with all predictor variables but the model is simpler and DBH and tree species information are not required. Which is a pluss as DBH and species information are not directly available in the target dataset but estimated from other variables. For the carbon storage and carbon sequestation models we see that DBH is important, and that importance drops when removing this variable. Therefore we select the model with tree height, crown area, pollution zone and DBH as predictor variables.

Bodø: 











### References
- Barton, D. and Venter, Z., 2022. NINA Project memo 397 
- Cimburova, Z., & Barton, D. N. (2020). The potential of geospatial analysis and Bayesian networks to enable i-Tree Eco assessment of existing tree inventories. Urban Forestry & Urban Greening, 55, 126801. https://doi.org/10.1016/j.ufug.2020.126801