# -*- coding: utf-8 -*-
"""
Created on Fri Sep 21 12:20:02 2018

@author: James Raines

Automated HIFLD data download. 
Requires downloading the HIFLD data catalog and renaming the REST API endpoint field to rest_endpoint and save as CSV.
Some ancillary fields interfer with geopandas ability to open the CSV and need to be deleted.
""" 

import geopandas as gpd
import os
import fiona
import requests
import pandas as pd
import io
import json
from time import time
 
def getGeoJson(rest_endpoint):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36'}
    payload = {'f': 'geojson', 'outSR': '4326', 'outFields': '*', 'where': '1%3D1'}
    baseURL = [rest_endpoint]
    baseURL.append('/query?')
    for i in payload:
        baseURL.append('&' + i + '=' + payload[i])
    query = ''.join(baseURL)
    try:
        r = requests.get(query, timeout=5, headers=headers)
        name = baseURL[0].split('/')[7]
        print(name, query)
        if r.status_code == 200:
            return r.json(), r.status_code, name
        else:
            print(404, query)
            return '', 404, query
    except:
        print(404, query)
        return '', 404, query 
 
def geojsonToShapefile(file_path, output_dir, output_name):
    t1 = time()
    print(file_path, output_dir, output_name)
    source_crs_wkt = fiona.open(file_path).meta['crs_wkt']
    df = gpd.read_file(file_path)
    try:
        df.to_file(filename=output_name, driver='ESRI Shapefile', crs_wkt=source_crs_wkt)
    except:
        print('Inputs not valid for data conversion')
    print('Elapsed time: ' + str(round(time() - t1, 2)) + ' seconds')
 
def getData(dataCatalog, outputDir)
    os.chdir(outputDir)
    for i in range(len(dataCatalog)):
        if i > 100 and i < 108:
            geoJson, status_code, name = getGeoJson(dataCatalog.iloc[i]['rest_endpoint'])
            if status_code == 200:
                print('code successful')
                with open('temporary_598c83h34e9e098e72s9e.json', 'w') as gj:
                    json.dump(geoJson, gj)
                    print(geoJson, gj)
                geojsonToShapefile('temporary_598c83h34e9e098e72s9e.json', outputDir, name + '.shp')
                gj.close()
                os.remove('temporary_598c83h34e9e098e72s9e.json')
            

# Define Inputs
dataCatalog = pd.read_csv('C:/test/HIFLD_2018_Data_Catalog.csv')
outputDir = r'C:\test/'

# Run function
getData(dataCatalog, outputDir)
