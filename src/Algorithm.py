"""algorithm.py

Functions related to

"""

import datetime
import logging
import pdb
import numpy as np
import rasterio

# logging levels = DEBUG, INFO, WARNING, ERROR, CRITICAL
logging.basicConfig(filename="../../output_data/logs/" \
                    + datetime.datetime.now().strftime("%d.%b_%Y_%H_%M_%S") \
                    + '.log', level=logging.INFO)


def compute_density_rasters(features, empty_raster):
    """ docstring"""
    open_raster = rasterio.open(empty_raster)
    eval_raster = open_raster.read()
    norm_raster = np.copy(eval_raster)
    request_counter = 0
    logging.info("Iterating through geojson objects...")

    for feat in features['features']:
        request_counter += 1
        if request_counter % 1000 == 0:
            logging.debug("Feature no. {}".format(request_counter))
        mask = rasterio.mask.raster_geometry_mask(open_raster, [feat['geometry']],
                                                  crop=False, invert=True)[0]

        props = feat['properties']
        if props['imageAnalysisResult'] == 1:
            norm_raster[0][mask] += 1
        elif (props['imageAnalysisResult'] == 0 or props['imageAnalysisResult'] == -1):
            norm_raster[0][mask] += 1
            eval_raster[0][mask] -= 1
        else:
            logging.warning("unexpected imageTestResult value: {}" \
                            .format(props['imageAnalysisResult']))
            logging.warning(feat)


    return eval_raster, norm_raster, request_counter

def solve(features, empty_raster, bin_output_path):
    """ docstring"""

    eval_raster, norm_raster, request_counter = compute_density_rasters(features, empty_raster)
    open_raster = rasterio.open(empty_raster)
    np.divide(eval_raster, norm_raster,
              out=np.zeros_like(eval_raster),
              where=norm_raster != 0)
    zero_mask = norm_raster[0] == 0
    logging.info("there was {} requests included in the analysis".format(request_counter))
    '''
    # Save the image into disk.
    img_output = rasterio.open(
        "../../output_data/35_norm_raster.tif",
        'w',
        driver='GTiff',
        nodata=nd,
        height=open_raster.height,
        width = open_raster.width,
        count=1,
        dtype = open_raster.dtypes[0],
        crs=open_raster.crs,
        transform=open_raster.transform)
    img_output.write(norm_raster)
    img_output.close()'''

    logging.info("request_counter: {}".format(request_counter))
    logging.debug("norm average: {}".format(np.average(norm_raster)))

    magic_constant = 0.075
    threshold = np.average(eval_raster)*magic_constant
    logging.debug("threshold is: {}".format(threshold))
    binary_raster = eval_raster > threshold
    binary_raster[0][zero_mask] = False

    # Save the image into disk.
    bin_output = rasterio.open(
        bin_output_path,
        'w',
        nbits=1,
        driver='GTiff',
        nodata=99,
        height=open_raster.height,
        width=open_raster.width,
        count=1,
        dtype='uint8',
        crs=open_raster.crs,
        transform=open_raster.transform)
    bin_output.write(binary_raster.astype(np.uint8))
    bin_output.close()

    logging.info("Algorithm finished, binary raster created")
