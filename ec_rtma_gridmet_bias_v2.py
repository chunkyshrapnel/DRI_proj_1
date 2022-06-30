# V2 creates each image and exports it one at a time.
# V1 creates all the images and then exports them as a batch.

import time
import ee
ee.Initialize()

# rtma collection (rename to like gridmet bands)
rtma_coll = ee.ImageCollection('projects/climate-engine/rtma/daily').\
    select(['TMAX', 'TMIN', 'WIND', 'SPH', 'SRAD', 'ETr', 'ETo'], ['tmmx', 'tmmn', 'vs', 'sph', 'srad', 'etr', 'eto'])

# gridmet collection
gridmet_coll = ee.ImageCollection("IDAHO_EPSCOR/GRIDMET").select(['tmmx', 'tmmn', 'vs', 'sph', 'srad', 'etr', 'eto'])

# month list
months = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

# year list
years = [2016, 2017, 2018, 2019, 2020, 2021]

# These are needed for exporting
gridmet_transform = [0.041666666666666664, 0, -124.78749996666667, 0, -0.041666666666666664, 49.42083333333334]
month_names = ee.List(['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'july', 'aug', 'sep', 'oct', 'nov', 'dec'])

# Notes for next time.
# Taking the mean of means =/= taking one big mean.

for month in months:

    # Filters all data by 'month' and by year
    for year in years:
        gridmet_monthly.append(gridmet_coll.filter(ee.Filter.calendarRange(month, month, 'month'))\
                                   .filter(ee.Filter.calendarRange(year, year, 'year'))\
                                   .mean()\
                                   .set('month', month))
                                   #do I set system:time_start here?

        rtma_monthly.append(rtma_coll.filter(ee.Filter.calendarRange(month, month, 'month'))\
                                   .filter(ee.Filter.calendarRange(year, year, 'year'))\
                                   .mean()\
                                   .set('month', month))
                                   #do I set system:time_start here?

    # Converts temp variable from Farenheight to Celcius
    temp_tmmn_tmmx = gridmet_monthly.select(['tmmn', 'tmmx']).subtract(273.15)
    gridmet_monthly = gridmet_monthly.addBands(**{'srcImg':temp_tmmn_tmmx, 'overwrite':True})

    # Same as 'gridmet_monthly' block but with rtma.


    # Reduces the resolution of the rtma collection to match the gridmet collection.
    g_proj = gridmet_coll.first().projection()
    rtma_monthly = rtma_monthly.reproject(g_proj).reduceResolution(**{'reducer': ee.Reducer.mean(), 'maxPixels': 64})

    # create bias collection by dividing RTMA by gridMET
    divide_ic = rtma_monthly.divide(gridmet_monthly).select(['vs', 'sph', 'srad', 'etr', 'eto'])
    subtract_ic = rtma_monthly.subtract(gridmet_monthly).select(['tmmn', 'tmmx'])
    bias = divide_ic.addBands(subtract_ic)

    # Export the bias layer to the repository at /bor-evap/assets/rtma_gridmet_bias
    month = month_names.get(month-1).getInfo()
    assetId = 'projects/bor-evap/assets/rtma_gridmet_bias/v1_1/monthly_from_py_v2/' + month
    task = ee.batch.Export.image.toAsset(**{
        'image': bias,
        'description': month,
        'assetId': assetId,
        'crs': 'EPSG:4326',
        'dimensions': '1386x585',
        'crsTransform': gridmet_transform
    })
    task.start()
    while task.active():
        print('Task Processing (id: {}).'.format(task.id))
        time.sleep(5)