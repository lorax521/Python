"""
Geocoding Services
['arcgis', 'azure', 'baidu', 'banfrance', 'bing', 'databc', 'geocodeearth', 'geocodefarm', 'geonames', 'google', 'googlev3', 'geolake', 'here', 'ignfrance', 'mapbox', 'opencage', 'openmapquest', 'pickpoint', 'nominatim', 'pelias', 'photon', 'liveaddress', 'tomtom', 'what3words', 'yandex']
"""

import geopandas as gpd
import pandas as pd
file = r'C:\Users\user\filename.csv'
df = pd.read_csv(file)
apiKey = 'SYlBs9Lv9TJRdaw1'
geocodingService = 'arcgis'

failed = []
geoms = pd.DataFrame()
for address in df['full']:
    try:
        geom = gpd.tools.geocode(address, provider=geocodingService, api_key=apiKey)
        geoms = geoms.append(geom.iloc[[0]])
        print('success: ' + address)
    except:
        failed.append(address)
        print('failed: ' + address)

df_wGeoms = df.merge(geoms, how='right')
gdf = gpd.GeoDataFrame(df_wGeoms)

output = r'C:\Users\user\file_geocoded.shp'
gdf.to_file(output, driver='ESRI Shapefile')
