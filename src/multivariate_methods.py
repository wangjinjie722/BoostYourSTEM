from .univariate_methods import load_data_frame
from .univariate_methods import get_var_info
import src.config as config
import pandas as pd
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from scipy import stats

np.random.seed(0)

from .univariate_methods import load_data_frame
from .univariate_methods import get_var_info

def get_feature_importance(field1,field2,file_loc="../../data/student_data.csv"):
    """
    This function describes how important a particular feature(variable our user choose) is to predict y value(outcome our user expect to see)
    
    :parameter x: two variable fields in our variables list, categorical type(gender or location) and numerical type(scale of something)
    :parameter y: a dependent y field(outcome our user expect to see)
    :return: For categorical fields: returns statistical test results,For numerical fields: returns pearson correlation coefficient between a field and y
    """
    
    df = load_data_frame(file_loc)
    df = df.dropna()
    x = df[field1]
    y = df[field2]

    # if x is numerical(continuous) field, we return the pearson correlation between a field and y
    # for the pearson correlation between a field and y, their size must be the same 
    if x.dtypes == 'float64' or 'int64':
        return stats.pearsonr(x, y)[0] # correlation coefficient
    else:
    # if x is categorical field, we return the statistical test results:
    # if x filed has 2 options like sex, we do the T-test(which is included by the ANOVA anlysis)
    # if x has more options like number of science courses, we do the ANOVA anlysis
        result = pd.concat([x,y],axis=1)
        df1 = [x for _, x in result.groupby(result[result.columns[0]])]
        data = []
        for i in range(1,len(df1)):
            data.append(df1[i][df1[i].columns[1]])
        return stats.f_oneway(*data)[1]
    return 'wrong data input'

def get_correlation_matrix(fields, file_loc="../data/student_data.csv"):
    '''
    Computes correlation matrix that captures correlation between features
    presented in the fields parameter

    :param fields: List of fields
    :type fields: list
    :param file_loc: Path to the dataset
    :type file_loc: str
    :returns: Correlation matrix.
    :rtype: pandas.DataFrame
    '''
    assert isinstance(fields, list), f"fields must be a list, not {type(fields)}"
    assert isinstance(file_loc, str), f"file_loc must be a string, not {type(file_loc)}"

    df = load_data_frame(file_loc)
    df_sub = df[fields]

    assert all([(isinstance(field, str) and field in df.columns) for field in fields])
    corrmat = df_sub.corr()

    return corrmat


class MLmodel:

    def __init__(self, file_loc=config.student_data_file):

        self.clf = None
        self.fields = None
        self.df = load_data_frame(file_loc)
        self.var_info = get_var_info()
        self.trained = False
        self.cat_cols = None
        self.cont_cols = None

    def train_model(self, y, fields, num_trees=100, test_split=0):
        '''
        train a machine learning model with y as dependent variable and variables in fields parameter as independent variables
        :param test_split: float, if non-zero, train-test split is performed and training and test accuracy is returned else
        model trained on complete data and training accuracy along with -1 in place of test accuracy returned.
        :param num_trees: number of estimators in the random forest model
        :param y: string, dependent variable, should be numerical/continuous
        :param fields: list,  list of independent variables, can be numerical or categorical
        :return: returns a tuple with training accuracy and test accuracy if test_split > 0 else a tuple with training accuracy
        and -1 in place of test accuracy.
        '''
        assert isinstance(fields, list)
        assert all([(isinstance(field, str) and field in self.var_info.index) for field in fields])
        assert y in self.var_info.index
        assert isinstance(num_trees, int) and num_trees > 0
        assert 0 <= test_split <= 1

        df_sub = self.df[fields + [y]]
        df_sub = df_sub.dropna()

        self.fields = fields
        Y = df_sub[y]
        df_sub = df_sub[fields]

        self.cat_cols = [field for field in fields if self.var_info.loc[field]['type'] == 'categorical']
        self.cont_cols = [field for field in fields if self.var_info.loc[field]['type'] == 'continuous']
        # print(f'Cat: {self.cat_cols} and cont: {self.cont_cols}')

        numeric_transformer = Pipeline(steps=[
            ('imputer', SimpleImputer(strategy='median')),
            ('scaler', StandardScaler())])

        categorical_transformer = Pipeline(steps=[
            ('imputer', SimpleImputer(strategy='constant', fill_value='missing')),
            ('onehot', OneHotEncoder(handle_unknown='ignore'))])

        preprocessor = ColumnTransformer(
            transformers=[
                ('num', numeric_transformer, self.cont_cols),
                ('cat', categorical_transformer, self.cat_cols)])

        # Append classifier to preprocessing pipeline.
        # Now we have a full prediction pipeline.
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.model_selection import train_test_split

        self.clf = Pipeline(steps=[('preprocessor', preprocessor),
                                   ('classifier', RandomForestRegressor(n_estimators=num_trees))])

        if test_split > 0:
            X_train, X_test, y_train, y_test = train_test_split(df_sub, Y, test_size=0.2)
            self.clf.fit(X_train, y_train)
            self.trained = True
            return self.clf.score(X_train, y_train), self.clf.score(X_test, y_test)
        else:
            self.clf.fit(df_sub, Y)
            self.trained = True
            return self.clf.score(df_sub, Y), -1

    def predict_model(self, input_data):
        '''
        returns model's prediction for the input_data
        :param input_data: dict, a dictionary with fields as keys and a scalar value or a list of values for each field,
        depending upon the number of samples
        :return: returns a 1-d numpy array with predicted y value for each sample
        '''

        assert isinstance(input_data, dict)
        assert all([field in self.fields for field in input_data.keys()]) and len(self.fields) == len(input_data.keys())

        if self.trained:
            test_data = pd.DataFrame()
            for field in self.fields:
                if isinstance(input_data[field], (list, tuple, np.ndarray)):
                    test_data[field] = input_data[field]
                else:
                    test_data[field] = [input_data[field]]
            return self.clf.predict(test_data)
        else:
            raise Exception("Model not trained")
