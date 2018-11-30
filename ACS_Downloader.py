import pandas as pd
import requests
import numpy as np
        
def get_acs_data(code_dictionary):
  """
  Fetches American Community Survey data from the 2015 ACS and returns it in a dataframe.
  Relies on an input dictionary that can be modified with any acs codes. See: https://api.census.gov/data/2015/acs5/variables.html
  
  param code_dictionary<dictionary>
  return df<Pandas Data Frame>
  """
    query = ['https://api.census.gov/data/2015/acs1?get=NAME']
    for key in code_dictionary: query.append(',' + code_dictionary[key])
    query.append('&for=state:*')
    query = ('').join(query)
    req = requests.get(query, timeout=3)
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

# update codes and name the columns
acs_codes = {
        'population': 'B01003_001E',
        'unemployed': 'B27011_014E',
        'employed': 'B27011_003E',
        'housing_units_without_mortgage': 'B25027_010E',
        'housing_units_with_mortgage': 'B25027_002E',
        }

acs_df = get_acs_data(acs_codes)
