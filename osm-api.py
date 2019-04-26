import requests
import os
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

# Set Proxies
os.environ["HTTP_PROXY"] = 'http://proxy.apps.dhs.gov:80'
os.environ["HTTPS_PROXY"] = 'http://proxy.apps.dhs.gov:80'

def getAmenities(amenity, bounding_box, buffer):
    overpass_url = "http://overpass-api.de/api/interpreter"
    overpass_query = """
    [bbox:"""+bounding_box+"""]
    [out:json];
    (node['amenity'='"""+amenity+"""'];
     way['amenity'='"""+amenity+"""'];
     rel['amenity'='"""+amenity+"""'];
    );
    out center;
    """
    response = requests.get(overpass_url, params={'data': overpass_query})
    data = response.json()
    
    if len(data['elements']) > 0:
        df = pd.DataFrame()
        
        for element in data['elements']:            
            try:
                df = df.append([[element['tags']['amenity'], Point(element['lon'], element['lat'])]])
            except:
                pass
            try:
                df = df.append([[element['tags']['amenity'], Point(element['center']['lon'], element['center']['lat'])]])
            except:
                pass
        df.columns = ['amenity', 'geometry']
            
        gdf = gpd.GeoDataFrame(df, geometry=df['geometry'])
#        intersect = gdf['geometry'].intersection(gpd.GeoSeries(buffer))
#        intersect.plot(figsize=(10, 10), edgecolor='#496d89', color='None')
#        print('returned ' + str(len(intersect)) + ' amenities: ' + amenity)
#        return intersect
        return gdf
    else: 
        print('No data found')
        
def getBuildings(bounding_box, buffer):
    overpass_url = "http://overpass-api.de/api/interpreter"
    overpass_query = """
    [bbox:"""+bounding_box+"""]
    [out:json];
    (node['building'];
     way['building'];
     rel['building'];
    );
    out center;
    """
    response = requests.get(overpass_url, params={'data': overpass_query})
    data = response.json()
    
    if len(data['elements']) > 0:
        df = pd.DataFrame()
        
        for element in data['elements']:            
            try:
                df = df.append([[element['tags']['amenity'], Point(element['lon'], element['lat'])]])
            except:
                pass
            try:
                df = df.append([[element['tags']['amenity'], Point(element['center']['lon'], element['center']['lat'])]])
            except:
                pass
        df.columns = ['amenity', 'geometry']
            
        gdf = gpd.GeoDataFrame(df, geometry=df['geometry'])
#        intersect = gdf['geometry'].intersection(gpd.GeoSeries(buffer))
#        intersect = intersect[intersect.geometry.notnull()]
#        intersect = gpd.GeoDataFrame(geometry=intersect.geometry)
#        intersect.plot(figsize=(10, 10), edgecolor='#496d89', color='None')
#        print('returned ' + str(len(intersect)) + ' buildings')
#        return intersect
        return gdf
    else: 
        print('No data found')

def buffer_bounding_box(point, buffer_distance):
    buffer = point.buffer(buffer_distance)
    bbox = buffer.bounds
    bbox_str = ','.join([str(x) for x in bbox])
    return bbox_str, buffer
    
def miles_from_lat(miles):
    return miles /69
    

denver = Point(39.748804, -104.994694)
austin = Point(30.272031, -97.743841)
dc = Point(38.900780, -77.036201)
bbox, buffer = buffer_bounding_box(austin, miles_from_lat(20))
gdf = getAmenities('police', bbox, buffer)
gdf = getBuildings(bbox, buffer)

# save to shapefile
outfile = r'C:\Users\jrainesi\Desktop\test/osm_test.shp'
#gdf.crs = {'init' :'epsg:4326'}
gdf.to_file(outfile, driver='ESRI Shapefile')

# amenities
# https://wiki.openstreetmap.org/wiki/Key:amenity
