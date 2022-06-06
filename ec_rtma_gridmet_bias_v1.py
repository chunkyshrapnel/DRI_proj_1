# Initialize and activate the Earth Engine module.
import ee
ee.Initialize()

# rtma collection (rename to like gridmet bands)
rtma_coll = ee.ImageCollection('projects/climate-engine/rtma/daily').select(['TMAX', 'TMIN', 'WIND', 'SPH', 'SRAD', 'ETr', 'ETo'], ['tmmx', 'tmmn', 'vs', 'sph', 'srad', 'etr', 'eto'])

# gridmet collection
gridmet_coll = ee.ImageCollection("IDAHO_EPSCOR/GRIDMET").select(['tmmx', 'tmmn', 'vs', 'sph', 'srad', 'etr', 'eto'])

# month list
months = ee.List.sequence(1, 12)
#months = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
#print("months", months)

years = ee.List.sequence(2016, 2021)
#print(years)
#years = [2016, 2017, 2018, 2019, 2020, 2021]
#print("years", years)

##########################################################################################
## Create mean monthly gridMET collection
## Map filtering and reducing across year-month combinations and convert to ImageCollection
def year_func_gridmet(y):
    def month_func_gridmet(m):
        return gridmet_coll.filter(ee.Filter.calendarRange(y, y, 'year')).\
            filter(ee.Filter.calendarRange(m, m, 'month')).\
            mean().\
            set('year', y).\
            set('month', m).\
            set('system:time_start', ee.Date.fromYMD(y, m, 1).millis())
    return months.map(month_func_gridmet)
images = years.map(year_func_gridmet).flatten()                                 #
grid_monthly_coll = ee.ImageCollection.fromImages(images)

##########################################################################################
## Convert the tmmx and tmmn values of grid_monthly_coll from Kelvin to Celcius 
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
## Create mean monthly RTMA collection
## Map filtering and reducing across year-month combinations and convert to ImageCollection
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
