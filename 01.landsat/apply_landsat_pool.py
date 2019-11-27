# -*- coding: utf-8 -*-
"""Load the models trained by train_rrc2OAC.py"""
import os
import sys
import time
import numpy as np
import matplotlib
import multiprocessing
from matplotlib import pyplot as plt
from netCDF4 import Dataset
import xgboost as xgb
import ctypes as c

matplotlib.use('agg')


def read_img_data(filename):
    """To read a netcdf file and return a dictionary"""
    from netCDF4 import Dataset

    # these wavelengths were from Acolite processing, which may be different from the seadas
    dict_waves = {'tm': [486, 571, 660, 839, 1678, 2217],
                  'etmp': [479, 561, 661, 835, 1650, 2208],
                  'oli': [483, 561, 655, 865, 1609, 2201]}
    gains = {'tm': [1.002, 1.012, 0.9796, 1.1150],
             'etmp': [0.9988, 0.9983, 0.9815, 1.1230],
             'oli': [1, 1, 1, 1]}
    offsets = {'tm': [0.0006, -0.0029, 0.0058, 0.0078],
               'etmp': [-0.0002, 0.0014, 0.0053, 0.0080],
               'oli': [0, 0, 0, 0]}

    mission = os.path.basename(filename).split('_')[0]
    if mission == 'L5':
        waves = dict_waves['tm']
        gain = gains['tm']
        offset = offsets['tm']
    elif mission == 'L7':
        waves = dict_waves['etmp']
        gain = gains['etmp']
        offset = offsets['etmp']
    elif mission == 'L8':
        waves = dict_waves['oli']
        gain = gains['oli']
        offset = offsets['oli']
    else:
        print('Program only supported the L5 TM, L7ETM+, L8OLI! Please check the data!')
        return None

    # read data
    nc = Dataset(filename, 'r')
    rrc_blue = np.array(nc['rhorc_' + str(waves[0])][:], dtype=np.float32)
    rrc_blue = rrc_blue * gain[0] + offset[0]

    rrc_green = np.array(nc['rhorc_' + str(waves[1])][:], dtype=np.float32)
    rrc_green = rrc_green * gain[1] + offset[1]

    rrc_red = np.array(nc['rhorc_' + str(waves[2])][:], dtype=np.float32)
    rrc_red = rrc_red * gain[2] + offset[2]

    rrc_nir = np.array(nc['rhorc_' + str(waves[3])][:], dtype=np.float32)
    rrc_nir = rrc_nir * gain[3] + offset[3]

    rrc_swir1 = np.array(nc['rhorc_' + str(waves[4])][:], dtype=np.float32)
    rrc_swir2 = np.array(nc['rhorc_' + str(waves[5])][:], dtype=np.float32)
    lat = np.array(nc['lat'][:], dtype=np.float32)
    lon = np.array(nc['lon'][:], dtype=np.float32)
    nc.close()
    nc = None

    print('>>> %s readed...' % filename)
    return rrc_blue, rrc_green, rrc_red, rrc_nir, rrc_swir1, rrc_swir2, lat, lon


def nc_write(ncfile, dataset, data, wavelength=None, global_dims=None,
             new=False, attributes=None, keep=True, offset=None,
             replace_nan=False, metadata=None, dataset_attributes=None, double=True,
             chunking=True, chunk_tiles=[10, 10], chunksizes=None,
             format='NETCDF4', nc_compression=True
             ):
    # This script was adapted from ACOLITE-QV
    from numpy import isnan, nan, float32, float64
    from math import ceil

    if os.path.exists(os.path.dirname(ncfile)) is False:
        os.makedirs(os.path.dirname(ncfile))

    dims = data.shape
    if global_dims is None: global_dims = dims

    if chunking:
        if chunksizes is not None:
            chunksizes = (ceil(dims[0] / chunk_tiles[0]), ceil(dims[1] / chunk_tiles[1]))

    if new:
        if os.path.exists(ncfile): os.remove(ncfile)
        nc = Dataset(ncfile, 'w', format=format)

        ## set global attributes
        setattr(nc, 'data source', 'ACOLITE L2 products')
        setattr(nc, 'Algorithm', ' xgboost algorithm')
        setattr(nc, 'generated_on', time.strftime('%Y-%m-%d %H:%M:%S'))
        setattr(nc, 'contact', 'Zhigang CAO')
        setattr(nc, 'product_type', 'NetCDF4')
        setattr(nc, 'Institute', 'NIGLAS, CAS')
        setattr(nc, 'version', '0.1 beta')

        if attributes is not None:
            for key in attributes.keys():
                if attributes[key] is not None:
                    try:
                        setattr(nc, key, attributes[key])
                    except:
                        print('Failed to write attribute: {}'.format(key))

        ## set up x and y dimensions
        nc.createDimension('x', global_dims[1])
        nc.createDimension('y', global_dims[0])
    else:
        nc = Dataset(ncfile, 'a', format=format)

    if (not double) & (data.dtype == float64):
        data = data.astype(float32)

    ## write data
    if dataset in nc.variables.keys():
        ## dataset already in NC file
        if offset is None:
            if data.dtype in (float32, float64): nc.variables[dataset][:] = nan
            nc.variables[dataset][:] = data
        else:
            if replace_nan:
                tmp = nc.variables[dataset][offset[1]:offset[1] + dims[0], offset[0]:offset[0] + dims[1]]
                sub_isnan = isnan(tmp)
                tmp[sub_isnan] = data[sub_isnan]
                nc.variables[dataset][offset[1]:offset[1] + dims[0], offset[0]:offset[0] + dims[1]] = tmp
                tmp = None
            else:
                nc.variables[dataset][offset[1]:offset[1] + dims[0], offset[0]:offset[0] + dims[1]] = data
    else:
        ## new dataset
        var = nc.createVariable(dataset, data.dtype, ('y', 'x'), zlib=nc_compression,
                                chunksizes=chunksizes, fill_value=-32767)
        if wavelength is not None: setattr(var, 'wavelength', float(wavelength))
        ## set attributes
        if dataset_attributes is not None:
            for att in dataset_attributes.keys():
                setattr(var, att, dataset_attributes[att])

        if offset is None:
            if data.dtype in (float32, float64): var[:] = nan
            var[:] = data
        else:
            if data.dtype in (float32, float64): var[:] = nan
            var[offset[1]:offset[1] + dims[0], offset[0]:offset[0] + dims[1]] = data
    if keep is not True: data = None

    ## close netcdf file
    nc.close()
    nc = None


def ostu_watermask(rrc_green, rrc_nir):
    import cv2 as cv
    from PIL import Image
    # ostu-method to determined the water mask
    ndwi = (rrc_green - rrc_nir) / (rrc_green + rrc_nir)
    ndwi[ndwi < -1] = np.nan
    ndwi[ndwi > 1] = np.nan
    # scale to 0-255
    ndwi = np.round((ndwi + 1) / 2 * 255).astype('uint8')
    im = Image.fromarray(ndwi)
    im.save("foo.png")
    # Otsu's thresholding
    ndwi = cv.imread("foo.png")
    ndwi = cv.cvtColor(ndwi, cv.COLOR_BGR2GRAY)
    thre1, img1 = cv.threshold(ndwi, 0, 255, cv.THRESH_BINARY + cv.THRESH_OTSU)
    os.remove("foo.png")
    return img1


def retrieve_chl_map(indices):
    arr = np.frombuffer(chl.get_obj())
    b = arr.reshape((line, col))

    r = rows[indices]
    c = cols[indices]

    dtrain = xgb.DMatrix([rrc[:, r, c], ])
    b[r, c] = bst.predict(dtrain)


def apply_model_pixel(rrc_blue, rrc_green, rrc_red, rrc_nir, rrc_swir1, rrc_swir2):
    # calculate pixel by pixel
    # using the water_mask to filter the land pixel and only calculate the water pixel
    # this is a strategy to save time
    global line
    global col
    line = rrc_blue.shape[0]
    col = rrc_blue.shape[1]

    # make a coarse atmospheric correction
    rrc_blue = rrc_blue - rrc_swir2
    rrc_green = rrc_green - rrc_swir2
    rrc_red = rrc_red - rrc_swir2
    rrc_nir = rrc_nir - rrc_swir2
    rrc_swir1 = rrc_swir1 - rrc_swir2

    # generate the band ratios and FAI
    gb = rrc_green / rrc_blue
    rb = rrc_red / rrc_blue
    ng = rrc_nir / rrc_green
    nr = rrc_nir / rrc_red
    fai = rrc_nir - (rrc_red + (rrc_swir1 - rrc_red) * (865.0 - 655.0) / (1609.0 - 655.0))

    # initial the global variables
    global rrc
    rrc = np.array([rrc_blue, rrc_green, rrc_red, rrc_nir, rrc_swir1, gb, rb, ng, nr, fai])
    global chl
    chl = multiprocessing.Array(c.c_double, line * col)
    # water mask
    water_mask = ostu_watermask(rrc_green, rrc_nir)
    # cloud mask
    cloud_threshold = 0.03

    # mask
    water_mask[rrc_swir2 >= cloud_threshold] = 0

    global rows
    global cols
    rows, cols = np.where(water_mask != 0)
    size = len(rows)
    interval = int(size / 20.0)

    # start to calculate
    print('start time is {}'.format(time.strftime('%Y-%m-%d %H:%M:%S')))
    # cores = multiprocessing.cpu_count()
    cores = 2
    pool = multiprocessing.Pool(processes=cores)
    cnt = 0
    n_elements = rows.size
    for _ in pool.imap_unordered(retrieve_chl_map, range(n_elements)):
        if cnt % interval == 0:
            sys.stdout.write('Scans %d in %d => %d processed.\n' % (cnt, n_elements, cnt/n_elements * 100))
        cnt += 1
    # pool.map(retrieve_chl_map, range(n_elements))
    print('end time is {}'.format(time.strftime('%Y-%m-%d %H:%M:%S')))

    # recover the data from shared buffer
    arr = np.frombuffer(chl.get_obj())
    chl_pred = arr.reshape((line, col))
    chl_pred[chl_pred<=0] = np.nan

    return chl_pred

def output_retrieval(l2r_ncfile, lat, lon, chlora):
    """Write the Chla, Lat, Lon to a nc file with a compression netcdf4 format"""
    l2r_nc_new = True
    nc_write(l2r_ncfile, 'latitude', lat, new=l2r_nc_new,
             dataset_attributes={'long_name': 'latitude', 'units': 'degree +north'})

    print('	+++ lat written in %s' % l2r_ncfile)
    l2r_nc_new = False

    nc_write(l2r_ncfile, 'longitude', lon, new=l2r_nc_new,
             dataset_attributes={'long_name': 'longitude', 'units': 'degree +east'})
    print('	+++ lon written in %s' % l2r_ncfile)

    nc_write(l2r_ncfile, 'chl_a', chlora, new=l2r_nc_new,
             dataset_attributes={'long_name': 'chlorophll-a', 'valid_min': 0.1,
                                 'valid_max': 100.0, 'units': 'mg m^-3'})
    print('	+++ Chl_a written in %s' % l2r_ncfile)


def plot_save_chlora(chl, outname):
    """Plot and save the image of Chla with a jet scratch color bar"""
    cmap = plt.cm.jet
    fig = plt.figure()
    canvas = matplotlib.backends.backend_agg.FigureCanvasAgg(fig)
    ax = fig.add_axes([0.1, 0.1, 0.8, 0.8])
    im = ax.imshow(chl, cmap=cmap, vmin=0, vmax=60)
    fig.colorbar(im, ax=ax, orientation='vertical', label='Chla(mug/L')
    ax.axis('off')
    canvas.print_figure(outname, dpi=300)
    print('>>> chlora png generated at :' + time.strftime('%Y-%m-%d %H:%M:%S'))


# global variables
# chl used she shared memory for the multiprocessing
chl = multiprocessing.Array(c.c_double, [])

rrc = []
rows = []
cols = []
line = []
col = []
# load model
model_path = '/Users/zhigang/Scripts/Python/landsat_chl_1984/model_v1/bst_chl_landsat_v1.model'
np.seterr(divide='ignore', invalid='ignore')
bst = xgb.Booster({'nthread': 4})  # init model
bst.load_model(model_path)

if __name__ == '__main__':
    import glob

    l2_dir = '/Users/zhigang/Desktop/SateliteData/landsat/'
    outputdir = '/Users/zhigang/Desktop/SateliteData/landsat/'  # define the filename

    filenames = glob.glob(l2_dir + '*_L2R.nc')
    print('>>> %d files will be proceed!' % len(filenames))

    i = 1
    for filename in filenames:
        print('%d/%d is processing...' % (i, len(filenames)))
        i = i + 1
        l2r_ncfile = os.path.join(outputdir,
                                  os.path.basename(filename).split('.')[0] + '_chl-pool.nc')

        if os.path.exists(l2r_ncfile):
            print('%s existed, skip.\n' % l2r_ncfile)
            continue

        # read the data
        rrc_blue, rrc_green, rrc_red, rrc_nir, rrc_swir1, rrc_swir2, lat, lon = read_img_data(filename)

        # apply the model to retrieve
        chl_pred = apply_model_pixel(rrc_blue, rrc_green, rrc_red, rrc_nir,
                                rrc_swir1, rrc_swir2)

        # writing data to a nc file
        output_retrieval(l2r_ncfile, lat, lon, chl_pred)
        print('>>> ' + l2r_ncfile + ' exported!')

        l2r_pltfile = os.path.splitext(l2r_ncfile)[0] + '.png'
        plot_save_chlora(chl_pred, l2r_pltfile)
        print('>>> ' + l2r_pltfile + ' exported!')
