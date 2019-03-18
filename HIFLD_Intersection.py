import geopandas as gpd
import os
import fiona
import requests
import pandas as pd
import json
import re
import uuid
import numpy as np
import matplotlib.pyplot as plt
from time import time
 
 
def getGeoJson(rest_endpoint):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36'}
#    headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
    payload = {'f': 'geojson', 'outSR': '4326', 'outFields': '*', 'where': '1%3D1'}
    baseURL = [rest_endpoint]
    baseURL.append('/query?')
    for i in payload:
        baseURL.append('&' + i + '=' + payload[i])
    query = ''.join(baseURL)
    try:
        r = requests.get(query, timeout=5, headers=headers)
        name = baseURL[0].split('/')[7]
        print('Processing request for ' + name)
        print('endpoint: ' + query)
        if r.status_code == 200:
            return r.json(), r.status_code, name, query
        else:
            print(404, query)
            return '', 404, query
    except:
        print(404, query)
        return '', 404, query 
 
def geojsonToShapefile(file_path, output_dir, output_name):
    source_crs_wkt = fiona.open(file_path).meta['crs_wkt']
    df = gpd.read_file(file_path)
    try:
        df.to_file(filename=output_name, driver='ESRI Shapefile', crs_wkt=source_crs_wkt)
        return True
    except:
        print('ERROR: Inputs not valid for data conversion')
        return False

def get_layers(layer_search):
    if len(layer_search) > 0:
        print('These are the indices found:')
        for i in enumerate(range(len(layer_search))): 
            print(i[0], layer_search.iloc[i[0]]['Layer Name'])
        decision = input('Would you like to search again? (y/n)')
        yes = ['Yes', 'yes', 'Y', 'y']
        no = ['No', 'no', 'N', 'n']
        if decision in yes:
            search_layer()
        elif decision in no:
            return(layer_search)        
        else:
            'Your input was invalid, try again'
    else:
        print('No layers were found with that key word')
        search_layer()
        
def select_data_layer(data_indexed):
    selectable_indices = list(np.arange(min(range(len(data_indexed))),max(range(len(data_indexed))) + 1))
    decision_index = input('Which index did you want to intersect?')
    if int(decision_index) in selectable_indices:
        data_selected = data_indexed.iloc[int(decision_index)]
        print(data_indexed.iloc[int(decision_index)]['Layer Name'] + ' selected')
        return(data_selected)
    else:
        print('Not a valid index')
        select_data(data_indexed)

def search_layer():
    # Set Proxies
    os.environ["HTTP_PROXY"] = 'http://proxy.apps.dhs.gov:80'
    os.environ["HTTPS_PROXY"] = 'http://proxy.apps.dhs.gov:80'
    
    input_data = input('What layer do you want to search for?')
    layer_search = dataCat[dataCat['Layer Name'].str.contains(input_data, flags=re.IGNORECASE)]
    data_indexed = get_layers(layer_search)
    selection = select_data_layer(data_indexed)
    name, rest = selection['Layer Name'], selection['Web Service URL from Source (REST Endpoint)']
    geojson, b, c, q = getGeoJson(rest)
    # create geojson from rest data
    temp_filename = str(uuid.uuid1()) + '.json' # unique temporary name
    with open(temp_filename, 'w') as gj:
        json.dump(geojson, gj)
        
    # read geojson and county data as geodataframes
    gdf = gpd.read_file(temp_filename) # read geojson into geodataframe
    os.remove(temp_filename) # deletes the temporary file
    plot_usa(gdf)
    return(gdf)
    
def select_county(layer_search):
    for i in enumerate(range(len(layer_search))): 
        dat = layer_search.iloc[i[0]]
        print(i[0], dat['NAME'], dat['State_Name'])
    decision = input('Would you like to search again? (y/n)')
    yes = ['Yes', 'yes', 'Y', 'y']
    no = ['No', 'no', 'N', 'n']
    if decision in yes:
        search_county()
    elif decision in no:
        return(layer_search)        
    else:
        'Your input was invalid, try again'
        
def select_data_county(data_indexed):
    selectable_indices = list(np.arange(min(range(len(data_indexed))),max(range(len(data_indexed))) + 1))
    decision_index = input('Which index did you want to intersect?')
    if int(decision_index) in selectable_indices:
        data_selected = data_indexed.iloc[[int(decision_index)]]
        print(data_indexed.iloc[int(decision_index)]['NAME'] + data_indexed.iloc[int(decision_index)]['State_Name'] + ' selected')
        return(data_selected)
    else:
        print('Not a valid index')
        select_data_county(data_indexed)
    
def search_county():
    counties = gpd.read_file('us_counties.shp')
    
    # selects all counties in region 8
    counties_r8 = counties[(counties['State_Abbr'] == 'CO') | 
            (counties['State_Abbr'] == 'UT') |
            (counties['State_Abbr'] == 'MT') |
            (counties['State_Abbr'] == 'ND') |
            (counties['State_Abbr'] == 'SD') |
            (counties['State_Abbr'] == 'WY')]
    
    # specify a key word for the counties you want to find
    input_county = input('What county are you searching for?')
    layer_search = counties_r8[counties_r8['NAME'].str.contains(input_county, flags=re.IGNORECASE)]
#    data_indexed = get_layers(layer_search)
    data_indexed = select_county(layer_search)
    selection = select_data_county(data_indexed)
    plot_usa(selection)
    return(selection)
    
def intersect():
    # specify a key word for the data you want to find
    hifld = search_layer()
    county = search_county()
    
    # perform intersect
    intersect = hifld[hifld.intersects(county.unary_union)]
    # set coordinate reference system
    intersect.crs = hifld.crs
    print('Intersection Map - Close Up')
    intersect.plot()
    print('Intersection Map')
    plot_usa(intersect)
    yes = ['Yes', 'yes', 'Y', 'y', 'sure', 'duh', 'oh yeah!']
    save_csv = input('Save a CSV of the intersect? (y/n)')
    save_shapefile = input('Save a Shapefile of the intersect? (y/n)')
    if save_csv in yes or save_shapefile in yes:
        output_name = input('What would you like to name your output?')
        # save to CSV or Shapefile
        if save_csv in yes:
            pd.DataFrame(intersect).to_csv(output_name + '.csv')
        if save_shapefile in yes:
            intersect.to_file(output_name + '.shp', driver='ESRI Shapefile')
    
    return(intersect, hifld, county)
    
def plot_usa(data):
    world = gpd.read_file(gpd.datasets.get_path('naturalearth_lowres'))
    
    # We restrict to South America.
    ax = world[world.name == 'United States'].plot(
        color='white', edgecolor='black')
    
    # We can now plot our GeoDataFrame.
    data.plot(ax=ax, color='red')
    
    plt.show()
    
# Point to the data catalog
os.chdir('C:/data/')
dataCat = pd.read_csv('HIFLD_2019_Data_Catalog.csv')

intersect, hifld, county = intersect()

