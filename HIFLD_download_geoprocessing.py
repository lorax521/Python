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
import json
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
            return r.json(), r.status_code, name
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

def getData(dataCatalog, outputDir, startIndex, endIndex):
    t1 = time()
    os.mkdir(outputDir)
    os.chdir(outputDir)
    for i in range(len(dataCatalog)):
        if i > startIndex and i < endIndex:
            geoJson, status_code, name = getGeoJson(dataCatalog.iloc[i]['rest_endpoint'])
            if status_code == 200:
                with open('temporary_598c83h34e9e098e72s9e.json', 'w') as gj:
                    json.dump(geoJson, gj)
                success = geojsonToShapefile('temporary_598c83h34e9e098e72s9e.json', outputDir, name + '.shp')
                gj.close()
                os.remove('temporary_598c83h34e9e098e72s9e.json')
                if success:
                    print(name + ' successful')
                else:
                    print(name + ' unsuccessful')
            print('')
    print('Total elapsed time: ' + str(round(time() - t1, 2)) + ' seconds')
    
def bufferIntersect(directory, buffer_size):
    os.chdir(directory)
    for file in os.listdir():
        if file.startswith('buffer_'):
            os.remove(file)
    for file in os.listdir():
        if file.endswith('.shp') and not file.startswith('buffer_'):
            print(file)
            shp = gpd.read_file(file)
            buffer = shp.buffer(buffer_size)
            source_crs_wkt = fiona.open(file).meta['crs_wkt']
            buffer.to_file(filename= 'buffer_' + file, driver='ESRI Shapefile', crs_wkt=source_crs_wkt)
    buffers = [x for x in os.listdir() if x.startswith('buffer_') and x.endswith('.shp')]
    shp1 = gpd.read_file(directory + buffers[0])
    shp2 = gpd.read_file(directory + buffers[1])
    shp1['const'] = 1
    shp2['const'] = 1
    intersect = shp1.dissolve('const').intersection(shp2.dissolve('const'))
    intersect.to_file(filename= 'intersect.shp', driver='ESRI Shapefile', crs_wkt=source_crs_wkt)
    for index in range(len(buffers)):
        if (index + 2) < len(buffers):
            print(index + 2)
            shp1 = gpd.read_file('intersect.shp')
            shp2 = gpd.read_file(directory + buffers[index + 2])
            shp1['const'] = 1
            shp2['const'] = 1
            intersect = shp1.dissolve('const').intersection(shp2.dissolve('const'))
            intersect.to_file(filename= 'intersect.shp', driver='ESRI Shapefile', crs_wkt=source_crs_wkt)
            

# Set Variables
os.chdir('C:/test/')
dataCatalog = pd.read_csv('HIFLD_2018_Data_Catalog.csv')
outputDir = 'HIFLD_requests'

# Run Functions
getData(dataCatalog, outputDir, 3, 8)
bufferIntersect('C:/test/HIFLD_requests/', 0.6)


"""
# in case the GeoSeries needs to be converted to a GeoDataFrame

gdf = gpd.GeoDataFrame()
gdf['geometry'] = intersect[intersect.geom_type == 'MultiPolygon']
gdf = gdf.rename(columns={0:'geometry'}).set_geometry('geometry')
gdf.plot(figsize=(15,15))
gdf.to_file(filename='intersect.shp', driver='ESRI Shapefile', crs_wkt=source_crs_wkt)
"""
