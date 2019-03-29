try: 
    import pandas as pd
    import pyodbc as py
    import shapely
    from shapely.wkt import loads
    from shapely.geometry import mapping, Polygon
    import fiona
    import geopandas
    import numpy as np
    import os
    import sys
    import shutil
except:
    import ctypes
    ctypes.windll.user32.MessageBoxW(None, u"Unable to open correctly: " + str(sys.exc_info()[1]), u'HAZUS - Message', 0)


def setup(scenario_name, folder_path):
    #Make a folder in folder_path for scenario_name
    if not os.path.exists(folder_path + '\\' + scenario_name):
        os.makedirs(folder_path + '\\' + scenario_name)
    #Connect to Hazus SQL Server database where scenario results are stored
    comp_name = os.environ['COMPUTERNAME']
    cnxn = py.connect('Driver=ODBC Driver 11 for SQL Server;SERVER=' +
    comp_name + '\HAZUSPLUSSRVR;DATABASE=' +
#    scenario_name + ';UID=hazuspuser;PWD=Gohazusplus_02') # old Hazus default user
    scenario_name + ';UID=SA;PWD=Gohazusplus_02') # new Hazus default user
    return comp_name, cnxn

def read_sql(comp_name, cnxn, scenario_name):
    #Select Hazus results from SQL Server scenario database
    sql_econ_loss = """SELECT Tract, SUM(ISNULL(BldgLoss, 0) +
    ISNULL(ContentLoss, 0) + ISNULL(InvLoss, 0) + ISNULL(RelocLoss, 0) +
    ISNULL(IncLoss, 0) + ISNULL(RentLoss, 0) + ISNULL(WageLoss, 0)) AS EconLoss
    FROM %s.dbo.[eqTractEconLoss]
    GROUP BY [eqTractEconLoss].Tract""" %scenario_name
    sql_county_fips = """SELECT Tract, {s}.dbo.hzCounty.CountyFips,
    {s}.dbo.hzCounty.CountyName, {s}.dbo.hzCounty.State FROM {s}.dbo.[hzTract]
    FULL JOIN {s}.dbo.hzCounty ON {s}.dbo.hzTract.CountyFips
    = {s}.dbo.hzCounty.CountyFips""".format(s=scenario_name)
    sql_demographics = """SELECT Tract, Population, Households FROM
    %s.dbo.[hzDemographicsT]""" %scenario_name
    sql_impact = """SELECT Tract, DebrisW, DebrisS,
    DisplacedHouseholds AS DisplHouse, ShortTermShelter AS Shelter
    FROM %s.dbo.[eqTract]""" %scenario_name
    sql_injury = """SELECT Tract, SUM(ISNULL(Level1Injury, 0)) AS Level1Injury,
    SUM(ISNULL(Level2Injury, 0)) AS Level2Injury,
    SUM(ISNULL(Level3Injury, 0)) AS Level3Injury, SUM(ISNULL(Level1Injury, 0) +
    ISNULL(Level2Injury, 0) + ISNULL(Level3Injury, 0)) AS NonFatal5p
    FROM %s.dbo.[eqTractCasOccup] WHERE CasTime = 'C' AND InOutTot = 'Tot'
    GROUP BY Tract""" %scenario_name
    sql_building_damage = """SELECT Tract, SUM(ISNULL(PDsNoneBC, 0)) As NoDamage,
    SUM(ISNULL(PDsSlightBC, 0) + ISNULL(PDsModerateBC, 0)) AS GreenTag,
    SUM(ISNULL(PDsExtensiveBC, 0)) AS YellowTag, SUM(ISNULL(PDsCompleteBC, 0))
    AS RedTag FROM %s.dbo.[eqTractDmg] WHERE DmgMechType = 'STR'
    GROUP BY Tract""" %scenario_name
    sql_building_damage_occup = """SELECT Occupancy, SUM(ISNULL(PDsNoneBC, 0))
    As NoDamage, SUM(ISNULL(PDsSlightBC, 0) + ISNULL(PDsModerateBC, 0))
    AS GreenTag, SUM(ISNULL(PDsExtensiveBC, 0)) AS YellowTag,
    SUM(ISNULL(PDsCompleteBC, 0)) AS RedTag FROM %s.dbo.[eqTractDmg]
    WHERE DmgMechType = 'STR' GROUP BY Occupancy""" %scenario_name
    sql_building_damage_bldg_type = """SELECT eqBldgType,
    SUM(ISNULL(PDsNoneBC, 0)) As NoDamage, SUM(ISNULL(PDsSlightBC, 0) +
    ISNULL(PDsModerateBC, 0)) AS GreenTag, SUM(ISNULL(PDsExtensiveBC, 0))
    AS YellowTag, SUM(ISNULL(PDsCompleteBC, 0)) AS RedTag
    FROM %s.dbo.[eqTractDmg] WHERE DmgMechType = 'STR'
    GROUP BY eqBldgType""" %scenario_name
    sql_spatial = """SELECT Tract, Shape.STAsText() AS Shape
    FROM %s.dbo.[hzTract]""" %scenario_name

    #Group tables and queries into iterable
    hazus_results = {'econ_loss': sql_econ_loss , 'county_fips': sql_county_fips,
                    'demographics': sql_demographics, 'impact': sql_impact,
                    'injury': sql_injury,'building_damage': sql_building_damage,
                    'building_damage_occup': sql_building_damage_occup,
                    'building_damage_bldg_type': sql_building_damage_bldg_type,
                    'tract_spatial': sql_spatial}
    #Read Hazus result tables from SQL Server into dataframes with Tract ID as index
    hazus_results_df = {table: pd.read_sql(query, cnxn) for table, query
    in hazus_results.items()}
    for name, dataframe in hazus_results_df.items():
        if (name != 'building_damage_occup') and (name != 'building_damage_bldg_type'):
            dataframe.set_index('Tract', append=False, inplace=True)
    return hazus_results_df

#Join and group Hazus result dataframes into final TwoPAGER dataframes
def results(hazus_results_df):
        tract_results = hazus_results_df['county_fips'].join([hazus_results_df['econ_loss'],
        hazus_results_df['demographics'], hazus_results_df['impact'],
        hazus_results_df['injury'], hazus_results_df['building_damage']])
        county_results = tract_results.groupby('CountyFips').agg({'CountyName':'first',
        'State':'first', 'EconLoss':'sum', 'Population':'sum', 'Households':'sum',
        'DebrisW':'sum', 'DebrisS':'sum','DisplHouse':'sum', 'Shelter':'sum',
        'Level1Injury':'sum', 'Level2Injury':'sum', 'Level3Injury':'sum',
        'NonFatal5p': 'sum', 'NoDamage':'sum', 'GreenTag':'sum', 'YellowTag':'sum',
        'RedTag':'sum'})
        return tract_results, county_results

def to_csv(hazus_results_df, tract_results, county_results, folder_path,
            scenario_name):
            #Export TwoPAGER dataframes to text files
            two_pager_df = {'building_damage_occup':
                        hazus_results_df['building_damage_occup'],
                        'building_damage_bldg_type':
                        hazus_results_df['building_damage_bldg_type'],
                        'tract_results': tract_results,
                        'county_results': county_results}
            for name, dataframe in two_pager_df.items():
                path = folder_path + '\\' + scenario_name + '\\' + name + '.txt'
                dataframe.to_csv(path)

#Create shapefile of TwoPAGER tract table
def to_shp(folder_path, scenario_name, hazus_results_df, tract_results):
        tract_shp = folder_path + '\\' + scenario_name + '\\tract_results.shp'
        schema = {
            'geometry': 'Polygon',
            'properties': {'Tract': 'str',
                            'CountyFips': 'int',
                            'EconLoss': 'float',
                            'Population': 'int',
                            'Households': 'int',
                            'DebrisW': 'float',
                            'DebrisS': 'float',
                            'DisplHouse': 'float',
                            'Shelter': 'float',
                            'NonFatal5p': 'float',
                            'NoDamage': 'float',
                            'GreenTag': 'float',
                            'YellowTag': 'float',
                            'RedTag': 'float'},
                            }
        with fiona.open(tract_shp,'w', driver='ESRI Shapefile', schema=schema,
        crs={'proj':'longlat', 'ellps':'WGS84', 'datum':'WGS84',
        'no_defs':True}) as c:
            for index, row in hazus_results_df['tract_spatial'].iterrows():
                for i in row:
                    tract = shapely.wkt.loads(i)
                    c.write({'geometry': mapping(tract),
                            'properties': {'Tract': index,
                            'CountyFips':
                            str(np.int64(tract_results.loc[str(index), 'CountyFips'])),
                            'EconLoss':
                            str(np.float64(tract_results.loc[str(index), 'EconLoss'])),
                            'Population':
                            str(np.int64(tract_results.loc[str(index), 'Population'])),
                            'Households':
                            str(np.int64(tract_results.loc[str(index), 'Households'])),
                            'DebrisW':
                            str(np.float64(tract_results.loc[str(index), 'DebrisW'])),
                            'DebrisS':
                            str(np.float64(tract_results.loc[str(index), 'DebrisS'])),
                            'DisplHouse':
                            str(np.float64(tract_results.loc[str(index), 'DisplHouse'])),
                            'Shelter':
                            str(np.float64(tract_results.loc[str(index), 'Shelter'])),
                            'NonFatal5p':
                            str(np.float64(tract_results.loc[str(index), 'NonFatal5p'])),
                            'NoDamage':
                            str(np.float64(tract_results.loc[str(index), 'NoDamage'])),
                            'GreenTag':
                            str(np.float64(tract_results.loc[str(index), 'GreenTag'])),
                            'YellowTag':
                            str(np.float64(tract_results.loc[str(index), 'YellowTag'])),
                            'RedTag':
                            str(np.float64(tract_results.loc[str(index), 'RedTag']))}
                                            })
            c.close()
            return tract_shp

def str_to_html(text, filename):
    output = open(filename,"w")
    output.write(text)
    output.close()
    
def shapefile_to_geojson(folder_path, scenario_name):
    gdf = geopandas.read_file(folder_path + '/' + scenario_name + '/tract_results.shp')
    with open(folder_path + '/' + scenario_name + '/' + 'data.js', 'w') as gj:
        gj.write('var data = ' + gdf.to_json())
    
#Roll up subfunctions into one overall function
def two_pager(scenario_name, folder_path):
    comp_name, cnxn = setup(scenario_name, folder_path)
    hazus_results_df = read_sql(comp_name, cnxn, scenario_name)
    tract_results, county_results = results(hazus_results_df)
    to_csv(hazus_results_df, tract_results, county_results, folder_path,
    scenario_name)
    to_shp(folder_path, scenario_name, hazus_results_df, tract_results)
    contents = generate_contents(hazus_results_df, tract_results, county_results, scenario_name, folder_path)
    str_to_html(contents, folder_path+'/' + scenario_name +'/' + scenario_name + '.html')
    shapefile_to_geojson(folder_path, scenario_name)
    print('Hazus earthquake results available locally at: ' + folder_path +
    '\\' + scenario_name)

def generate_contents(hazus_results_df, tract_results, county_results, scenario_name, folder_path):
    # move images
    try:
        shutil.copytree(r'C:/HazusData/export_script_images', folder_path + '/' + scenario_name + '/images')
    except:
        print('cannot copy images')
    
    def f(number, digits=0):
        try:
            f_str = str("{:,}".format(round(number, digits)))
            if ('.' in f_str) and (digits==0):
                f_str = f_str.split('.')[0]
            if (number > 1000000000) and (number < 1000000000000):
                split = f_str.split(',')
                f_str = split[0] + '.' + split[1] + ' bil'
            return f_str
        except:
            return str(number)
    
    RES = hazus_results_df['building_damage_occup'].loc[(hazus_results_df['building_damage_occup'].Occupancy.str.startswith('RES'))]
    COM = hazus_results_df['building_damage_occup'].loc[(hazus_results_df['building_damage_occup'].Occupancy.str.startswith('COM'))]
    IND = hazus_results_df['building_damage_occup'].loc[(hazus_results_df['building_damage_occup'].Occupancy.str.startswith('IND'))]
    AGR = hazus_results_df['building_damage_occup'].loc[(hazus_results_df['building_damage_occup'].Occupancy.str.startswith('AGR'))]
    GOV = hazus_results_df['building_damage_occup'].loc[(hazus_results_df['building_damage_occup'].Occupancy.str.startswith('GOV'))]
    REL = hazus_results_df['building_damage_occup'].loc[(hazus_results_df['building_damage_occup'].Occupancy.str.startswith('REL'))]
    EDU = hazus_results_df['building_damage_occup'].loc[(hazus_results_df['building_damage_occup'].Occupancy.str.startswith('EDU'))]
    
    #economic loss by county
    econloss = county_results.sort_values(by='EconLoss', ascending=False)[0:7]
    econloss_total = sum(county_results['EconLoss'])
    # non fatal injuries by county
    nonfatals = county_results.sort_values(by='NonFatal5p', ascending=False)[0:7]
    nonfatals_total = round(sum(county_results['NonFatal5p']))
    # shelter needs by county
    shelter_needs = county_results.sort_values(by='Shelter', ascending=False)[0:7]
    shelter_needs_total = round(sum(county_results['Shelter']))
    # debris
    debris_s_total = round(sum(county_results['DebrisS']))
    debris_w_total = round(sum(county_results['DebrisW']))
    
    econloss_high = np.percentile(tract_results['EconLoss'], 75)
    econloss_med = np.percentile(tract_results['EconLoss'], 50)
    econloss_low = np.percentile(tract_results['EconLoss'], 25)
    
    if len(econloss < 7):
        new_rows = 7 - len(econloss)
        for row in range(new_rows):
            new_row = pd.Series(list(map(lambda x: ' ', econloss.columns)), index=econloss.columns)
            econloss = econloss.append([new_row])
            nonfatals = nonfatals.append([new_row])
            shelter_needs = shelter_needs.append([new_row])         
    
    contents = '''
    <!doctype html>
    <html lang="en">
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
        <!-- Leaflet CSS -->
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.4.0/dist/leaflet.css"/>
        <!-- Bootstrap CSS -->
        <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css"/>
        <!-- Font Awesome -->
        <link rel="stylesheet" href="https://use.fontawesome.com/releases/v5.8.1/css/all.css" integrity="sha384-50oBUHEmvpQ+1lW4y57PTFmhCaXp0ML5d60M1M7uH2+nqUivzIebhndOJK28anvf" crossorigin="anonymous">
        <style>
            body {
                position: absolute;
            }
            h3 {
                font-size: 1rem;
                font-weight: bold;
                background: #38a9e4;
                color: #ffffff;
                padding: 1% 0% 1% 3%;
                margin: 0%;
            }
            .page {
                width: 8.3in;
                height: 10.8in;
                margin-left: 0.1in;
            }
            .header {
                top: 5px;
                border: 2px solid lightgrey;
                height: 9%;
                width: 88%;
                margin: 2% 2% 0 2%;
                display: inline-flex;
                justify-content: space-between;
            }
            .header-left {
                background: white;
                color: slategrey;
                font-weight: bold;
                width: 88%;
                font-family: Helvetica Neue,Helvetica,Arial,sans-serif; 
            }
            .header-right {
                width: 10%;
                height: auto;
            }
            .header h1 {
                font-size: 2rem;
                margin: 0.5rem;
                font-weight: bold;
            }
            .header h2 {
                font-size: 1.2rem;
                margin-left: 0.5rem;
            }
            .header-border:first-child {
                height: 1%;
                background: #38a9e4;
                width: 96%;
                margin: 1% 2% -1% 2%;
            }
            .header-border {
                height: 1%;
                background: #38a9e4;
                width: 96%;
                margin: 1% 0% -1% 2%;
            }
            .img-container {
                width: 10%;
                height: auto;
                right: 9%;
                top: 1.5%;
                position: absolute;
            }
            .header img {
                width: 169%;
                height: auto;
                background: white;
                padding: 2%;
            }
            .content {
                display: inline-flex;
                width: 100%;
                height: 88%;
            }
            .column {
                width: 47%;
                height: 96%;
                margin: 2%;
            }
            .map-box {
                width: 100%;
                height: 38%;
                display: inline-block;
            }
            .table {
                margin-bottom: 0.5rem;
            }
            .data-table-totals {
                width: 100%;
            }
            .table thead th {
                background: #0e7c7b;
                color: white;
                border-right: 1px solid white;
                text-align: center;
                font-size: 64%;
            }
            .table td, .table th {
                padding: 0.4% !important;
                font-size: 76%;
            }
            .heading-total {
                background: #38a9e4;
                color: white;
                position: relative;
                z-index: -2;
            }
            .heading-total-debris {
                padding-bottom: 5%;
            }
            .heading-total h3 {
                font-size: 16px;
                display: inline-block;
                width: 40%;
                padding: 1% 0% 0% 3%;
            }
            .heading-total h4 {
                font-size: 81%;
                display: inline-block;
                position: absolute;
                top: 30%;
                right: 35%;
            }
            .circle{
                display: inline-block;
                width:18%;
                border-radius:50%;
                text-align:center;
                font-size: 64%;
                padding:9% 0;
                line-height:0;
                position:relative;
                color: white;
                font-family: Helvetica, Arial Black, sans;
                position: absolute;
                right: 15%;
                top: -23%;
                z-index: -1;
                border: 2px solid #ffffff;
                font-weight: bold;
            }
            #map-1 {
                width: 100%;
                height: 100%;
            }
            #map-2 {
                width: 100%;
                height: 100%;
            }
            .tag-icon {
                position: absolute;
                transform: rotate(45deg);
                font-size: 1000%;       
            }
            .tag-table {
                position: absolute;
                font-size: 57%;
                z-index: 10;
                list-style-type: none;
                top: 18%;
                left: 23%;
                font-weight: bold;
            }
            .tag-table tr td:last-child {
                text-align: end;
            }
            .tag {
                width: 8em;
                position: relative;
                margin-top: 6%;
            }
            .tags h1 {
                position: absolute;
                top: 10px;
                font-size: 85%;
                left: 27%;
                width: 70%;
                text-align: center;
                /* color: white; */
                /* font-weight: bold; */
                border-radius: 50%;
                padding-bottom: 50%;
                margin-top: -8%;
                padding-top: 9px;
    
            }
            .green-bg {
                background: #2aac6e;
            }
            .yellow-bg {
                background: #ebe07c;
            }
            .red-bg {
                background: #d04751;
            }
            .green-cl {
                color: #2aac6e;
            }
            .yellow-cl {
                color: #ebe07c;
            }
            .red-cl {
                color: #d04751;
            }
            .tag .circle {
                border: none;
                width: 14%;
                padding: 7%;
                background: #fff;
                right: 31%;
                top: -11%;
                z-index: 11;
            }
            .tags {
                display: inline-flex;
                justify-content: space-between;
                height: 19%;
                margin-left: -5%;
            }
            @media print{
                .table thead th {
                    background: #0e7c7b !important;
                }
                .table-striped tbody tr:nth-of-type(2n+1) {
                    background-color: rgba(0,0,0,.05) !important;
                }
                /* .table td, .table tr:nth-of-type(2n+1) {  */
                .odd { 
                    /* -webkit-print-color-adjust: exact; */
                    background-color: red !important; 
                    background: red !important; 
                } 
                .leaflet-control {
                    display: none !important;
                }
            }
        </style>
        <title>Hazus Export</title>
    </head>
    <body>
        <div class="page">
            <div class="header-border"></div>
            <div class="header">
                <div class="header-left">
                    <h1>Alaska, M7.0 Earthquake</h1>
                    <h2>30 November 2018</h2>
                </div>
                <div class="header-right">
                    <img src='./images/Hazus Logo_Blue.png'>
                    <img src='./images/FEMA_logo.svg'>
                </div>
            </div>
            <div class="header-border"></div>
            <div class="content">
                <div class="column">
                    <div class="tags">
                        <div class="tag">
                            <table class='tag-table'>
                                <tr>
                                    <td>Residential</td>
                                    <td>'''+f(sum(RES['GreenTag']))+'''</td>
                                </tr>
                                <tr>
                                    <td>Commercial</td>
                                    <td>'''+f(sum(COM['GreenTag']))+'''</td>
                                </tr>
                                <tr>
                                    <td>Industrial</td>
                                    <td>'''+f(sum(IND['GreenTag']))+'''</td>
                                </tr>
                                <tr>
                                    <td>Agricultural</td>
                                    <td>'''+f(sum(AGR['GreenTag']))+'''</td>
                                </tr>
                                <tr>
                                    <td>Educational</td>
                                    <td>'''+f(sum(EDU['GreenTag']))+'''</td>
                                </tr>
                                <tr>
                                    <td>Government</td>
                                    <td>'''+f(sum(GOV['GreenTag']))+'''</td>
                                </tr>
                                <tr>
                                    <td>Religious</td>
                                    <td>'''+f(sum(REL['GreenTag']))+'''</td>
                                </tr>
                            </table>
                            <i class="fa fa-tag tag-icon green-cl" aria-hidden="true"></i>
                            <h1 class="green-bg">Inspected</h1>
                            <div class="circle"></div>
                        </div>
                        <div class="tag">
                            <table class='tag-table'>
                                <tr>
                                    <td>Residential</td>
                                    <td>'''+f(sum(RES['YellowTag']))+'''</td>
                                </tr>
                                <tr>
                                    <td>Commercial</td>
                                    <td>'''+f(sum(COM['YellowTag']))+'''</td>
                                </tr>
                                <tr>
                                    <td>Industrial</td>
                                    <td>'''+f(sum(IND['YellowTag']))+'''</td>
                                </tr>
                                <tr>
                                    <td>Agricultural</td>
                                    <td>'''+f(sum(AGR['YellowTag']))+'''</td>
                                </tr>
                                <tr>
                                    <td>Educational</td>
                                    <td>'''+f(sum(EDU['YellowTag']))+'''</td>
                                </tr>
                                <tr>
                                    <td>Government</td>
                                    <td>'''+f(sum(GOV['YellowTag']))+'''</td>
                                </tr>
                                <tr>
                                    <td>Religious</td>
                                    <td>'''+f(sum(REL['YellowTag']))+'''</td>
                                </tr>
                            </table>
                            <i class="fa fa-tag tag-icon yellow-cl" aria-hidden="true"></i>
                            <h1 class="yellow-bg">Restricted</h1>
                            <div class="circle"></div>
                        </div>
                        <div class="tag">
                            <table class='tag-table'>
                                <tr>
                                    <td>Residential</td>
                                    <td>'''+f(sum(RES['RedTag']))+'''</td>
                                </tr>
                                <tr>
                                    <td>Commercial</td>
                                    <td>'''+f(sum(COM['RedTag']))+'''</td>
                                </tr>
                                <tr>
                                    <td>Industrial</td>
                                    <td>'''+f(sum(IND['RedTag']))+'''</td>
                                </tr>
                                <tr>
                                    <td>Agricultural</td>
                                    <td>'''+f(sum(AGR['RedTag']))+'''</td>
                                </tr>
                                <tr>
                                    <td>Educational</td>
                                    <td>'''+f(sum(EDU['RedTag']))+'''</td>
                                </tr>
                                <tr>
                                    <td>Government</td>
                                    <td>'''+f(sum(GOV['RedTag']))+'''</td>
                                </tr>
                                <tr>
                                    <td>Religious</td>
                                    <td>'''+f(sum(REL['RedTag']))+'''</td>
                                </tr>
                            </table>
                            <i class="fa fa-tag tag-icon red-cl" aria-hidden="true"></i>
                            <h1 class="red-bg">Unsafe</h1>
                            <div class="circle"></div>
                        </div>
                    </div>
                    <div class="data-table-totals">
                        <div class="heading-total">
                            <h3>Economic Loss by County</h3>
                            <h4>Total:</h4>
                            <div class="circle">$'''+f(econloss_total)+'''</div>
                        </div>
                        <table class="table table-striped">
                            <thead>
                                <tr>
                                <th scope="col">County</th>
                                <th scope="col">State</th>
                                <th scope="col">Total ($)</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td>'''+str(econloss['CountyName'].iloc[0])+'''</td>
                                    <td>'''+str(econloss['State'].iloc[0])+'''</td>
                                    <td>'''+f(econloss['EconLoss'].iloc[0], 2)+'''</td>
                                </tr>
                                <tr>
                                    <td>'''+str(econloss['CountyName'].iloc[1])+'''</td>
                                    <td>'''+str(econloss['State'].iloc[1])+'''</td>
                                    <td>'''+f(econloss['EconLoss'].iloc[1], 2)+'''</td>
                                </tr>
                                <tr>
                                    <td>'''+str(econloss['CountyName'].iloc[2])+'''</td>
                                    <td>'''+str(econloss['State'].iloc[2])+'''</td>
                                    <td>'''+f(econloss['EconLoss'].iloc[2], 2)+'''</td>
                                </tr>
                                <tr>
                                    <td>'''+str(econloss['CountyName'].iloc[3])+'''</td>
                                    <td>'''+str(econloss['State'].iloc[3])+'''</td>
                                    <td>'''+f(econloss['EconLoss'].iloc[3], 2)+'''</td>
                                </tr>
                                <tr>
                                    <td>'''+str(econloss['CountyName'].iloc[4])+'''</td>
                                    <td>'''+str(econloss['State'].iloc[4])+'''</td>
                                    <td>'''+f(econloss['EconLoss'].iloc[4], 2)+'''</td>
                                </tr>
                                <tr>
                                    <td>'''+str(econloss['CountyName'].iloc[5])+'''</td>
                                    <td>'''+str(econloss['State'].iloc[5])+'''</td>
                                    <td>'''+f(econloss['EconLoss'].iloc[5], 2)+'''</td>
                                </tr>
                                <tr>
                                    <td>'''+str(econloss['CountyName'].iloc[6])+'''</td>
                                    <td>'''+str(econloss['State'].iloc[6])+'''</td>
                                    <td>'''+f(econloss['EconLoss'].iloc[6], 2)+'''</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    <div class="data-table-totals">
                        <div class="heading-total">
                            <h3>Non-Fatal Injuries by County</h3>
                            <h4>Total:</h4>
                            <div class="circle">'''+f(nonfatals_total)+'''</div>
                        </div>
                        <table class="table table-striped">
                                <thead>
                                    <tr>
                                    <th scope="col">County</th>
                                    <th scope="col">State</th>
                                    <th scope="col">Population</th>
                                    <th scope="col">Injuries</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr>
                                        <td>'''+str(nonfatals['CountyName'].iloc[0])+'''</td>
                                        <td>'''+str(nonfatals['State'].iloc[0])+'''</td>
                                        <td>'''+f(nonfatals['Population'].iloc[0])+'''</td>
                                        <td>'''+f(nonfatals['NonFatal5p'].iloc[0])+'''</td>
                                    </tr>
                                    <tr>
                                        <td>'''+str(nonfatals['CountyName'].iloc[1])+'''</td>
                                        <td>'''+str(nonfatals['State'].iloc[1])+'''</td>
                                        <td>'''+f(nonfatals['Population'].iloc[1])+'''</td>
                                        <td>'''+f(nonfatals['NonFatal5p'].iloc[1])+'''</td>
                                    </tr>
                                    <tr>
                                        <td>'''+str(nonfatals['CountyName'].iloc[2])+'''</td>
                                        <td>'''+str(nonfatals['State'].iloc[2])+'''</td>
                                        <td>'''+f(nonfatals['Population'].iloc[2])+'''</td>
                                        <td>'''+f(nonfatals['NonFatal5p'].iloc[2])+'''</td>
                                    </tr>
                                    <tr>
                                        <td>'''+str(nonfatals['CountyName'].iloc[3])+'''</td>
                                        <td>'''+str(nonfatals['State'].iloc[3])+'''</td>
                                        <td>'''+f(nonfatals['Population'].iloc[3])+'''</td>
                                        <td>'''+f(nonfatals['NonFatal5p'].iloc[3])+'''</td>
                                    </tr>
                                    <tr>
                                        <td>'''+str(nonfatals['CountyName'].iloc[4])+'''</td>
                                        <td>'''+str(nonfatals['State'].iloc[4])+'''</td>
                                        <td>'''+f(nonfatals['Population'].iloc[4])+'''</td>
                                        <td>'''+f(nonfatals['NonFatal5p'].iloc[4])+'''</td>
                                    </tr>
                                    <tr>
                                        <td>'''+str(nonfatals['CountyName'].iloc[5])+'''</td>
                                        <td>'''+str(nonfatals['State'].iloc[5])+'''</td>
                                        <td>'''+f(nonfatals['Population'].iloc[5])+'''</td>
                                        <td>'''+f(nonfatals['NonFatal5p'].iloc[5])+'''</td>
                                    </tr>
                                        <td>'''+str(nonfatals['CountyName'].iloc[6])+'''</td>
                                        <td>'''+str(nonfatals['State'].iloc[6])+'''</td>
                                        <td>'''+f(nonfatals['Population'].iloc[6])+'''</td>
                                        <td>'''+f(nonfatals['NonFatal5p'].iloc[6])+'''</td>
                                    </tr>
                                </tbody>
                            </table>
                    </div>
                    <div class="data-table-totals">
                        <div class="heading-total">
                            <h3>Shelter Needs by County</h3>
                            <h4>Total:</h4>
                            <div class="circle">'''+f(shelter_needs_total)+'''</div>
                        </div>
                        <table class="table table-striped">
                                <thead>
                                    <tr>
                                    <th scope="col">County</th>
                                    <th scope="col">State</th>
                                    <th scope="col">Population</th>
                                    <th scope="col">Households</th>
                                    <th scope="col">People Needing Shelter</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr>
                                        <td>'''+str(shelter_needs['CountyName'].iloc[0])+'''</td>
                                        <td>'''+str(nonfatals['State'].iloc[0])+'''</td>
                                        <td>'''+f(nonfatals['Population'].iloc[0])+'''</td>
                                        <td>'''+f(nonfatals['Households'].iloc[0])+'''</td>
                                        <td>'''+f(nonfatals['Shelter'].iloc[0])+'''</td>
                                    </tr>
                                    <tr>
                                        <td>'''+str(shelter_needs['CountyName'].iloc[1])+'''</td>
                                        <td>'''+str(nonfatals['State'].iloc[1])+'''</td>
                                        <td>'''+f(nonfatals['Population'].iloc[1])+'''</td>
                                        <td>'''+f(nonfatals['Households'].iloc[1])+'''</td>
                                        <td>'''+f(nonfatals['Shelter'].iloc[1])+'''</td>
                                    </tr>
                                    <tr>
                                        <td>'''+str(shelter_needs['CountyName'].iloc[2])+'''</td>
                                        <td>'''+str(nonfatals['State'].iloc[2])+'''</td>
                                        <td>'''+f(nonfatals['Population'].iloc[2])+'''</td>
                                        <td>'''+f(nonfatals['Households'].iloc[2])+'''</td>
                                        <td>'''+f(nonfatals['Shelter'].iloc[2])+'''</td>
                                    </tr>
                                    <tr>
                                        <td>'''+str(shelter_needs['CountyName'].iloc[3])+'''</td>
                                        <td>'''+str(nonfatals['State'].iloc[3])+'''</td>
                                        <td>'''+f(nonfatals['Population'].iloc[3])+'''</td>
                                        <td>'''+f(nonfatals['Households'].iloc[3])+'''</td>
                                        <td>'''+f(nonfatals['Shelter'].iloc[3])+'''</td>
                                    </tr>
                                    <tr>
                                        <td>'''+str(shelter_needs['CountyName'].iloc[4])+'''</td>
                                        <td>'''+str(nonfatals['State'].iloc[4])+'''</td>
                                        <td>'''+f(nonfatals['Population'].iloc[4])+'''</td>
                                        <td>'''+f(nonfatals['Households'].iloc[4])+'''</td>
                                        <td>'''+f(nonfatals['Shelter'].iloc[4])+'''</td>
                                    </tr>
                                    <tr>
                                        <td>'''+str(shelter_needs['CountyName'].iloc[5])+'''</td>
                                        <td>'''+str(nonfatals['State'].iloc[5])+'''</td>
                                        <td>'''+f(nonfatals['Population'].iloc[5])+'''</td>
                                        <td>'''+f(nonfatals['Households'].iloc[5])+'''</td>
                                        <td>'''+f(nonfatals['Shelter'].iloc[5])+'''</td>
                                    </tr>
                                    <tr>
                                        <td>'''+str(shelter_needs['CountyName'].iloc[6])+'''</td>
                                        <td>'''+str(nonfatals['State'].iloc[6])+'''</td>
                                        <td>'''+f(nonfatals['Population'].iloc[6])+'''</td>
                                        <td>'''+f(nonfatals['Households'].iloc[6])+'''</td>
                                        <td>'''+f(nonfatals['Shelter'].iloc[6])+'''</td>
                                    </tr>
                                </tbody>
                            </table>
                    </div>
                </div>
                <div class="column">
                    <h3>Economic Loss by County</h3>
                    <div class="legend">
                        <div class="legend-1">'''+'< '+f(econloss_low)+'''</div>
                        <div class="legend-2">'''+f(econloss_low)+ '-'+f(econloss_med)+'''</div>
                        <div class="legend-3">'''+f(econloss_med)+ '-'+f(econloss_high)+'''</div>
                        <div class="legend-4">'''+'< '+f(econloss_high)+'''</div>
                    </div>
                    <div class="map-box">
                        <div id="map-1"></div>
                    </div>
                    <h3>Incident Extent</h3>
                    <div class="map-box">
                        <div id="map-2"></div>
                    </div>
                    <div class="data-table-totals">
                        <div class="heading-total heading-total-debris">
                            <h3>Debris</h3>
                            <h4>Total:</h4>
                            <div class="circle">'''+f(debris_w_total + debris_s_total)+'''</div>
                        </div>
                        <table class="table table-striped">
                                <thead>
                                    <tr>
                                        <th scope="col">Type</th>
                                        <th scope="col">Tons</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <!--<tr>
                                        <td>Tree</td>
                                        <td>4,562</td>
                                    </tr>-->
                                    <tr>
                                        <td>Brick/Wood</td>
                                        <td>'''+f(debris_w_total)+'''</td>
                                    </tr>
                                    <tr>
                                        <td>Conrete/Steel</td>
                                        <td>'''+f(debris_s_total)+'''</td>
                                    </tr>
                                </tbody>
                            </table>
                    </div>
                </div>
            </div>
        </div>
        <!-- Leaflet -->
        <script src="https://unpkg.com/leaflet@1.4.0/dist/leaflet.js"></script>
        <!-- jQuery first, then Popper.js, then Bootstrap JS -->
        <script src="https://code.jquery.com/jquery-3.3.1.slim.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.14.7/umd/popper.min.js"></script>
        <script src="https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/js/bootstrap.min.js"></script>
        <script src="data.js"></script>
        <script>
            function buildMap(map_id) {
                var map = L.map(map_id, {zoomControl:false}).setView([34.763635, -78.912921], 7);
                
                var Esri_WorldStreetMap = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}');
                
                const Esri_WorldImagery = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}');
                
                // with attribution
                // var Esri_WorldStreetMap = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}', {
                //     attribution: 'Tiles &copy; Esri &mdash; Source: Esri, DeLorme, NAVTEQ, USGS, Intermap, iPC, NRCAN, Esri Japan, METI, Esri China (Hong Kong), Esri (Thailand), TomTom, 2012'
                // });
                
                // const Esri_WorldImagery = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
                // attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
                // });
                
                map_id == 'map-1' ? Esri_WorldStreetMap.addTo(map) : Esri_WorldImagery.addTo(map);
                
                const basemaps = {
                'default': Esri_WorldStreetMap,
                'satellite': Esri_WorldImagery
                };
                
                const overlays = {};
                
                L.control.layers(basemaps, overlays, {position: 'topleft'}).addTo(map);
                
                function style(feature) {
                    return {
                        "color": "#4d4dff",
                        "weight": 0.3,
                        "fillOpacity": 0.6,
                        "fillColor": getColor(feature.properties.EconLoss)
                    };
                }
                function highlightFeature(e) {
                    var layer = e.target;
    
                    layer.setStyle({
                        weight: 3,
                        color: '#666',
                        dashArray: '',
                        fillOpacity: 0.7
                    });
    
                    if (!L.Browser.ie && !L.Browser.opera && !L.Browser.edge) {
                        layer.bringToFront();
                    }
                }
    
                function resetStyle(e) {
                    dataLayer.resetStyle(e.target);
                }
                function getColor(d) {
                    return d >= '''+str(econloss_high)+''' ? '#cb181d' :
                        d >= '''+str(econloss_med)+''' ? '#fb6a4a' :
                        d >= '''+str(econloss_low)+''' ? '#fcae91' :
                                    '#fee5d9';
                }
                function onEachFeature(feature, layer) {
                    layer.bindPopup(`<strong>County FIPS: </strong>${feature.properties.CountyFips}
                    <br><strong>Green Tag: </strong>${feature.properties.GreenTag}
                    <br><strong>Yellow Tag: </strong>${feature.properties.YellowTag}
                    <br><strong>Red Tag: </strong>${feature.properties.RedTag}
                    <br><strong>Economic Loss: </strong>${feature.properties.EconLoss}
                    <br><strong>Population: </strong>${feature.properties.Population}
                    <br><strong>Households: </strong>${feature.properties.Households}
                    <br><strong>Shelter Needed: </strong>${feature.properties.Shelter}
                    <br><strong>Debris W: </strong>${feature.properties.DebrisW}
                    <br><strong>Debris S: </strong>${feature.properties.DebrisS}
                    <br>
                    `);
                    layer.on({
                        mouseover: highlightFeature,
                        mouseout: resetStyle
                    });
                }
                function pointToLayer(feature, latlng) {
                    var layer =  L.circleMarker(latlng, {
                        radius: 4,
                        fillColor: "#027bce",
                        color: "#63595c",
                        weight: 1,
                        opacity: 0.9,
                        fillOpacity: 0.8
                    });
                    layer.bindPopup(`<strong>County FIPS: </strong>${feature.properties.CountyFips}
                        <br><strong>Green Tag: </strong>${feature.properties.GreenTag}
                        <br><strong>Yellow Tag: </strong>${feature.properties.YellowTag}
                        <br><strong>Red Tag: </strong>${feature.properties.RedTag}
                        <br><strong>Economic Loss: </strong>${feature.properties.EconLoss}
                        <br><strong>Population: </strong>${feature.properties.Population}
                        <br><strong>Households: </strong>${feature.properties.Households}
                        <br><strong>Shelter Needed: </strong>${feature.properties.Shelter}
                        <br><strong>Debris W: </strong>${feature.properties.DebrisW}
                        <br><strong>Debris S: </strong>${feature.properties.DebrisS}
                        <br>
                    `);
                    return layer;
                }
                var dataLayer = L.geoJSON(data, {
                    style: style,
                    onEachFeature: onEachFeature,
                    pointToLayer: pointToLayer
                }).addTo(map);
    
                map.fitBounds(dataLayer.getBounds());
                zoomLevel = map.getZoom();
                map.setZoom(zoomLevel + 1)
            }
            
            buildMap('map-1');
            buildMap('map-2');
        
        </script>
    </body>
    </html>
    '''

    return contents


two_pager('hazus_scenario_name','output_directory')

