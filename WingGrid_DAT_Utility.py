try:
    import sys
    if sys.version[0] == '2':
        import Tkinter as tk
        from Tkinter import *
        import tkMessageBox as messagebox
        import tkFileDialog as filedialog
    else:
        import tkinter as tk
        from tkinter import *
        from tkinter import messagebox
        from tkinter import filedialog
    
    import arcpy
    from arcpy.sa import *
    import pandas as pd
    from time import time
    arcpy.CheckOutExtension('Spatial')
except:
    tk.messagebox.showerror("Hazus Message Bot", "You don't have the necessary Python packages to run this app. This app requires Tkinter, ArcPy, Pandas, and Time.")

#tk.messagebox.showinfo("Please wait while the app initalizes.")

# Create app
root = tk.Tk()


# App parameters
root.title('HAZUS - Wind Gust DAT Generator')
root.geometry('600x480')
root.configure(background='#282a36')

# App Functions
def retrieve_textHeader():
    return text_header.get("1.0",'end-1c')

def retrieve_pathlabelWindGrid():
    return pathlabel_windgrid['text']

def retrieve_pathlabelCentroid():
    return pathlabel_centroids['text']

def browsefunc_windgrid():
    filename = filedialog.askopenfilename()
    pathlabel_windgrid.config(text=filename)

def browsefunc_centroids():
    filename = filedialog.askopenfilename()
    pathlabel_centroids.config(text=filename)

def browsefunc_dat():
    filename = filedialog.asksaveasfile(defaultextension=".DAT")
    pathlabel_dat.config(text=filename.name)

def run():
    input_windgrid = pathlabel_windgrid['text']
    input_centroids = pathlabel_centroids['text']
    DATHeaderList = text_header.get("1.0",'end-1c').split(';')
    input_DAT_header = list(map(lambda x: x[1:] if x.startswith('\n') else x, DATHeaderList))
    output_DAT = pathlabel_dat['text']
    lat = '{0:.4f}'.format(float(text_lat.get("1.0",'end-1c')))
    lng = '{0:.4f}'.format(float(text_lng.get("1.0",'end-1c')))
    for i in [input_windgrid, input_centroids, input_DAT_header, output_DAT, lat, lng]: print(i)
    # execute function ☼
    try:
        generateWindSpeedDAT(input_windgrid, input_centroids, input_DAT_header, output_DAT, lat, lng)
    except:
        tk.messagebox.showerror("Unable to process. Please check your imports and try again.")

def printElapsedTime(message, t0):
    """
    message<input>: string
    t0<input>: time()
    """
    if (time() - t0) > 3600:
        print(message + '... at ' + str(round((time() - t0)/3600, 4)) + ' hours')
    if (time() - t0) > 60:
        print(message + '... at ' + str(round((time() - t0)/60, 3)) + ' minutes')
    else:
        print(message + '... at ' + str(round(time() - t0, 2)) + ' seconds')

def generateWindSpeedDAT(input_windgrid, input_centroids, input_DAT_header, output_DAT, lat, lng):
    """
    input_windgrid<input>: string; ESRI feature class
    input_centroids<input>: string; ESRI feature class
    input_DAT_header<input>: list<string>
    output_DAT<output>: string; relative or absolute path with output file name
    """
    t0 = time()
    # interpolates the wind speeds
    idw = Idw(input_windgrid, 'Vg_mph')
    printElapsedTime('Wind speed interpolation complete', t0)
    # adds the wind speeds to the census tract centroids
    ExtractValuesToPoints(input_centroids, idw, 'in_memory/windSpeedCentroids')
    printElapsedTime('Values extracted to centroids', t0)

    # creates a dataframe with only the necessary fields
    fields = ('FIPS', 'CenLongit', 'CenLat', 'RASTERVALU')
    df = pd.DataFrame(arcpy.da.FeatureClassToNumPyArray('in_memory/windSpeedCentroids', fields))
    # changes mph to m/s
    df['RASTERVALU'] = df['RASTERVALU'] * 0.44704
    # formats the data with appropriate spacing for HAZUS
    tracts = list(map(lambda x: x + '    ', df.FIPS))
    longs = list(map(lambda x: '{0:.4f}'.format(x) + '   ', df.CenLongit))
    lats = list(map(lambda x: '{0:.4f}'.format(x) + '      ', df.CenLat))
    windSpeeds = list(map(lambda x: '{0:.5f}'.format(x) + '     ', df.RASTERVALU))
    zeros = list(map(lambda x: '0' + '{0:.5f}'.format(x * 0) + '    ', df.RASTERVALU))
    windSpeedsLast = list(map(lambda x: '{0:.5f}'.format(x), df.RASTERVALU))
    # organizes the newly formatted data into a dataframe
    dfout = pd.DataFrame({'tracts': tracts, 'longs': longs, 'lats': lats, 'windSpeeds': windSpeeds, 'zeros': zeros, 'windSpeedsLast': windSpeedsLast})
    dfout = dfout[['tracts', 'longs', 'lats', 'windSpeeds', 'zeros', 'windSpeedsLast']]

    # opens the export DAT file
    export=open(output_DAT, "w")

    # adds columns to the DAT file header
    input_DAT_header.append('Landfall position:     ' + lng + '      ' + lat)
    input_DAT_header.append('')
    input_DAT_header.append('      ident        elon      nlat         ux          vy        w (m/s)')
    printElapsedTime('Data formatted for export', t0)

    # writes header to DAT file
    for row in input_DAT_header:
        export.write(row + '\n')

    # writes data to DAT file
    for row in range(len(dfout[dfout.columns[0]])):
        writeRow = ''
        for item in dfout.iloc[row]:
            writeRow = writeRow + item
        export.write(writeRow + '\n')
    export.close()

    # clears in memory workspace
    arcpy.Delete_management('in_memory')
    printElapsedTime('Total elapsed time', t0)
    tk.messagebox.showinfo("HAZUS - Wind Gust DAT Generator", "Process complete. Your DAT file has been created.")


# App body
# DAT header
label_header = tk.Label(root, text='Enter DAT file header. *Must have 3 lines seperated by semicolins*', font='Helvetica 10 bold', bg='#282a36', fg='#f8f8f2')
label_header.grid(row=0, column=0, pady=(10, 5), padx=20, sticky=W)

text_header = tk.Text(root, height=3, width=80, bg='#FFFFFF', fg='#282a36', relief=FLAT, font='Helvetica 10')
text_header.grid(row=1, column=0, pady=(0, 20), padx=20)
text_header.insert(END, 'Florence 2018: ARA Day7 as of 09/21/2018;\nMAXIMUM 3 SECOND WINDS AT 2010 CENSUS TRACK CENTROIDS FOR OPEN TERRAIN;\nSwath domain provided by FEMA')

# Specify impact lat lng
label_windgrid = tk.Label(root, text='Input: Specify landfall position in latitude and longitude', font='Helvetica 10 bold', bg='#282a36', fg='#f8f8f2')
label_windgrid.grid(row=3, column=0, padx=20, pady=(0, 10), sticky=W)

label_lat = tk.Label(root, text='Latitude: ', font='Helvetica 8 bold', bg='#282a36', fg='#f8f8f2')
label_lat.grid(row=4, column=0, sticky=W, pady=(0, 5), padx=40)
text_lat = tk.Text(root, height=1, width=15, relief=FLAT)
text_lat.grid(row=4, column=0, pady=(0, 5), sticky=W, padx=120)
text_lat.insert(END, '')

label_lng = tk.Label(root, text='Longitude: ', font='Helvetica 8 bold', bg='#282a36', fg='#f8f8f2')
label_lng.grid(row=5, column=0, sticky=W, padx=40)
text_lng = tk.Text(root, height=1, width=15, relief=FLAT)
text_lng.grid(row=5, column=0, pady=(0, 0), sticky=W, padx=120)
text_lng.insert(END, '')

# Browse for input windgrid
label_windgrid = tk.Label(root, text='Input: Select windgrid shapefile (.shp)', font='Helvetica 10 bold', bg='#282a36', fg='#f8f8f2')
label_windgrid.grid(row=6, column=0, pady=(20, 0), padx=20, sticky=W)

browsebutton_windgrid = tk.Button(root, text="Browse", command=browsefunc_windgrid, relief=FLAT, bg='#44475a', fg='#f8f8f2', cursor="hand2", font='Helvetica 8 bold')
browsebutton_windgrid.grid(row=6, column=0, pady=(20, 0), padx=(375, 0), sticky=W)

pathlabel_windgrid = tk.Label(root, bg='#282a36', fg='#f8f8f2', font='Helvetica 8')
pathlabel_windgrid.grid(row=7, column=0, pady=(0, 20), padx=40, sticky=W)

# Browse for input centroids
label_centroids = tk.Label(root, text='Input: Select centroids shapefile (.shp)', font='Helvetica 10 bold', bg='#282a36', fg='#f8f8f2')
label_centroids.grid(row=8, column=0, padx=20, sticky=W)

browsebutton_centroids = tk.Button(root, text="Browse", command=browsefunc_centroids, relief=FLAT, bg='#44475a', fg='#f8f8f2', cursor="hand2", font='Helvetica 8 bold')
browsebutton_centroids.grid(row=8, column=0, padx=(375, 0), sticky=W)

pathlabel_centroids = tk.Label(root, bg='#282a36', fg='#f8f8f2', font='Helvetica 8')
pathlabel_centroids.grid(row=9, column=0, pady=(0, 20), padx=40, sticky=W)

# Out DAT file name
label_dat = tk.Label(root, text='Output: Enter a name for the output DAT file.', font='Helvetica 10 bold', bg='#282a36', fg='#f8f8f2')
label_dat.grid(row=10, column=0, padx=20, sticky=W)

browsebutton_dat = tk.Button(root, text="Browse", command=browsefunc_dat, relief=FLAT, bg='#44475a', fg='#f8f8f2', cursor="hand2", font='Helvetica 8 bold')
browsebutton_dat.grid(row=10, column=0, padx=(375, 0), sticky=W)

pathlabel_dat = tk.Label(root, bg='#282a36', fg='#f8f8f2', font='Helvetica 8')
pathlabel_dat.grid(row=11, column=0, pady=(0, 20), padx=40, sticky=W)

button_run = tk.Button(root, text='Run', width=20, command=run, relief=FLAT, bg='#6272a4', fg='#f8f8f2', cursor="hand2", font='Helvetica 8 bold')
button_run.grid(row=12, column=0, pady=(0, 30))

# Run app
root.mainloop()
