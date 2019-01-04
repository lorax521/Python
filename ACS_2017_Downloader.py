import pandas as pd
import requests
import numpy as np
import os

def get_acs_data(code_dictionary):
    """
    Gets American Community Survey data from the 2017 5 year ACS and returns it in a dataframe.
    Query examples: https://api.census.gov/data/2017/acs/acs5/examples.html
    Variables: https://api.census.gov/data/2017/acs/acs5/variables.html
    Misc codes: https://www.census.gov/data/developers/data-sets/acs-1year/data-notes.html
  
    param code_dictionary<input>: dictionary
    return df<output>: pd.DataFrame
    """
    query = ['https://api.census.gov/data/2017/acs/acs5?get=']
    for key in enumerate(code_dictionary):
        if key[0] > len(code_dictionary) - 2:
            query.append(code_dictionary[key[1]])
        else:
            query.append(code_dictionary[key[1]] + ',')
    query.append('&for=county:*')
    query = ('').join(query)
    req = requests.get(query)
    reqArray = np.array(req.json())
    df = pd.DataFrame(reqArray)
    column_names = []
    for code in df.iloc[0]:
        try:
            column_names.append(list(acs_codes.keys())[list(acs_codes.values()).index(code)])
        except:
            column_names.append(code)
    df.columns = column_names
    df = df[1:]
    print(df.head())
    print('DataFrame shape: ' + str(df.shape))
    return df


# Set environment
os.environ["HTTP_PROXY"] = 'http://proxy.apps.dhs.gov:80'
os.environ["HTTPS_PROXY"] = 'http://proxy.apps.dhs.gov:80'
pd.set_option('display.float_format', lambda x: '%.3f' % x)

# update codes and name the columns
acs_codes = {
    'population': 'B01003_001E',
    'unemployed': 'B27011_014E',
    'employed': 'B27011_003E',
    'housing_units_without_mortgage': 'B25027_010E',
    'housing_units_with_mortgage': 'B25027_002E',
    'less_than_high_school': 'B06009_002E',
    'high_school': 'B06009_003E',
    'some_college': 'B06009_004E',
    'bachelors': 'B06009_005E',
#    'graduate_or_professional': 'B06009_006E',
#    'median_income': 'B06011_001E',
#    'poverty': 'B17001_002E',
#    'owner_occupied': 'B25003_002E',
#    'renter_occupied': 'B25003_003E',
#    'with_mortgage': 'B992522_002E',
#    'without_mortgage': 'B992522_005E',
#    'median_home_value': 'B25077_001E',
#    'median_housing_cost': 'B25105_001E',
#    'seasonal_rec_occasional_vacancy': 'B25004_006E',
#    'White': 'B03002_003E',
#    'Black': 'B03002_004E',
#    'American Indian': 'B03002_005E',
#    'Asian': 'B03002_006E',
#    'Pacific Islander': 'B03002_007E',
#    'Hispanic_Latino': 'B03002_012E',
#    'Other_race': 'B03002_008E',
#    'limited_english': 'B16003_001E',
    'under_18': 'B09001_001E',
    'over_65': 'B09020_001E',
    'geoid': 'GEO_ID',
    'name': 'NAME'
}

acs_df = get_acs_data(acs_codes)
acs_df.to_csv('acs_data.csv')
