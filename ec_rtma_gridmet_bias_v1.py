# Initialize and activate the Earth Engine module.
import ee
ee.Initialize()

# rtma collection (rename to like gridmet bands)
rtma_coll = ee.ImageCollection('projects/climate-engine/rtma/daily').select(['TMAX', 'TMIN', 'WIND', 'SPH', 'SRAD', 'ETr', 'ETo'], ['tmmx', 'tmmn', 'vs', 'sph', 'srad', 'etr', 'eto'])

# gridmet collection
gridmet_coll = ee.ImageCollection("IDAHO_EPSCOR/GRIDMET").select(['tmmx', 'tmmn', 'vs', 'sph', 'srad', 'etr', 'eto'])

# month list
months = ee.List.sequence(1, 12)

# years list
years = ee.List.sequence(2016, 2021)

##########################################################################################
# Create mean monthly gridMET collection
# Map filtering and reducing across year-month combinations and convert to ImageCollection
def year_func_gridmet(y):
    def month_func_gridmet(m):
        return gridmet_coll.filter(ee.Filter.calendarRange(y, y, 'year')).\
            filter(ee.Filter.calendarRange(m, m, 'month')).\
            mean().\
            set('year', y).\
            set('month', m).\
            set('system:time_start', ee.Date.fromYMD(y, m, 1).millis())
    return months.map(month_func_gridmet)

images = years.map(year_func_gridmet).flatten()
grid_monthly_coll = ee.ImageCollection.fromImages(images)

##########################################################################################
# Convert the tmmx and tmmn values of grid_monthly_coll from Kelvin to Celcius
def temp_conversion_func(image):
    temp_gridmet_image = image.select(['tmmx', 'tmmn']).subtract(273.15)
    temp_gridmet_image = image.addBands(temp_gridmet_image, None, True)
    return temp_gridmet_image

grid_monthly_coll = grid_monthly_coll.map(temp_conversion_func)

# Gridmet mean of monthly means colleciton
def mean_of_means_gridmet(m):
    return grid_monthly_coll.\
        filter(ee.Filter.calendarRange(m, m, 'month')).\
        mean().\
        set('month', m)

images = months.map(mean_of_means_gridmet).flatten()
grid_mean = ee.ImageCollection.fromImages(images)

##########################################################################################
# Create mean monthly RTMA collection
# Map filtering and reducing across year-month combinations and convert to ImageCollection
def year_func_rtma(y):
    def month_func_rtma(m):
        return gridmet_coll.filter(ee.Filter.calendarRange(y, y, 'year')).\
            filter(ee.Filter.calendarRange(m, m, 'month')).\
            mean().\
            set('year', y).\
            set('month', m).\
            set('system:time_start', ee.Date.fromYMD(y, m, 1).millis())
    return months.map(month_func_rtma)

images = years.map(year_func_rtma).flatten()                                 #
rtma_monthly_coll = ee.ImageCollection.fromImages(images)

# RTMA mean of monthly means colleciton
def mean_of_means_rtma(m):
    return rtma_monthly_coll.\
        filter(ee.Filter.calendarRange(m, m, 'month')).\
        mean().\
        set('month', m)

images = months.map(mean_of_means_rtma).flatten()
rtma_mean = ee.ImageCollection.fromImages(images)

# resample and reproj rtma collection to gridMET grid
g_proj = gridmet_coll.first().projection()
def reproj_func(image):
    return image.resample('bilinear').reproject(g_proj)

rtma_mean_rs = rtma_mean.map(reproj_func)

##########################################################################################
# create bias collection by dividing RTMA by gridMET (divde is performed foe earch matched
# pair of bands in image1 and image2 )
def bias_collection_funct(m):
    divide_ic = rtma_mean_rs.filter(ee.Filter.eq('month', m)).first() \
        .divide(grid_mean.filter(ee.Filter.eq('month', m)).first()) \
        .set('month', m) \
        .set('version', 1) \
        .select(['vs', 'sph', 'srad', 'etr', 'eto']);

    subtract_ic = rtma_mean_rs.filter(ee.Filter.eq('month', m)).first() \
        .subtract(grid_mean.filter(ee.Filter.eq('month', m)).first()) \
        .set('month', m) \
        .set('version', 1) \
        .select(['tmmx', 'tmmn']);

    return divide_ic.addBands(subtract_ic)

images = months.map(bias_collection_funct).flatten()
bias = ee.ImageCollection.fromImages(images)

##########################################################################################
# Export the bias layer to the repository at /bor-evap/assets/rtma_gridmet_bias
gridmet_transform = [0.041666666666666664, 0, -124.78749996666667, 0, -0.041666666666666664, 49.42083333333334]
month_names = ee.List(['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'july', 'aug', 'sep', 'oct', 'nov', 'dec'])
size = bias.size().getInfo()
listOfImage = bias.toList(size)
import time

for i in range(size):
    img = ee.Image(listOfImage.get(i))
    month = month_names.get(i).getInfo()
    assetId = 'projects/bor-evap/assets/rtma_gridmet_bias/v1/monthly/'+month
    args_dict = {
        'image': img,
        'description': month,
        'assetId': assetId,
        'crs': 'EPSG:4326',
        'dimensions': '1386x585',
        'crsTransform': gridmet_transform
    }
    task = ee.batch.Export.image.toAsset(**args_dict)
    task.start()
    while task.active():
        print('Task Processing (id: {}).'.format(task.id))
        time.sleep(5)

