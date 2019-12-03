"""validation.py

Functionality to validate results from the main part of this tool
by comparing them against the service's data fetched from the server.
"""

import os
import logging
import io
import csv
import pdb
import datetime
import numpy as np
from PIL import Image
from osgeo import ogr, gdal
import rasterio.features
import geojson
import requests

# logging levels = DEBUG, INFO, WARNING, ERROR, CRITICAL
logging.basicConfig(filename="../../output_data/logs/" \
                    + datetime.datetime.now().strftime("%d.%b_%Y_%H_%M_%S") \
                    + '.log', level=logging.INFO)





def write_statistics(output_path, service_number, layer_name, pixels_count, correct_pixels,
                     false_pos_pixels, false_neg_pixels, bbox_area_decrease):
    """Write statistics to a spreadsheet.

    :param str output_path: Path to the folder where statistics file will be written
    :param str service_number: Number of the service
    :param str layer_name: Name of the layer
    :param int pixels_count: Total number of pixels in validation
    :param int correct_pixels: Number of correctly determined pixels
    :param int false_pos_pixels: Number of pixels for which the tool's result
                                 was positive but there was no data in the location
                                 in the fetched layer
    :param int false_neg_pixels: Number of pixels for which the tool's result
                                 was negative but there was  data in the location
                                 in the fetched layer
    :param float bbox_area_decrease: Size of a bounding box that encapsulates
                                  area with data as determined by the tool;
                                  expressed in % of the original bounding box
    """
    stats_path = os.path.split(output_path)[0] + "/stats_"\
                               + datetime.datetime.now().strftime("%d.%b_%Y") + ".csv"

    if not os.path.isfile(stats_path):
        with open(stats_path, "w") as stats_file:
            headers = ["Service number", "Layer name", "Pixel count",\
                       "Correct", "False positives", "False negatives",\
                       "Area of new bounding box in %% of original"]
            row = [service_number, layer_name, pixels_count, correct_pixels,\
                   false_pos_pixels, false_neg_pixels, bbox_area_decrease]
            writer = csv.writer(stats_file)
            writer.writerow(headers)
            writer.writerow(row)

    else:
        with open(stats_path, "a") as stats_file:
            row = [service_number, layer_name, pixels_count, correct_pixels,\
                   false_pos_pixels, false_neg_pixels, bbox_area_decrease]
            writer = csv.writer(stats_file)
            writer.writerow(row)

    logging.info("Statistics written to {}".format(stats_path))


def area_decrease(bbox, data_bounds):
    """Write statistics to a spreadsheet

    :param list bbox: Bounding box as specified in the layer metadata
    :param list data_bounds: Bounding box that encapsulates
                             area with data as determined by the tool

    :return float: Size of data_bounds expressed as a percentage
                   of bbox
    """
    if len(data_bounds) == 0:
        # No bounds means no data found -> 100% decrease
        return 100
    x_decr = (data_bounds[2] - data_bounds[0])/(bbox[2] - bbox[0])
    y_decr = (data_bounds[3] - data_bounds[1])/(bbox[3] - bbox[1])

    return round(x_decr*y_decr*100)


def test_pixel(image):
    """Search for variation in a numpy array

    :param numpy array image: Array of numerical values

    :return boolean: Return True if there is variation in the array
    """
    uniques = np.unique(image)
    if len(uniques) == 1 and uniques[0] in [0, 255]:
        return False

    return True

    '''for i in range(image.shape[0]):
        for j in range(image.shape[1]):
            try:
                if not np.array_equal(image[i][j], first_val):
                    return True
            except UnboundLocalError:
                first_val = image[i][j]

    return False'''

def test_for_var(image):
    """Search for variation within each part of a 3x3 grid of the input image.

    If variation is found, corresponding value in the data_grid
    is set to True. If not, it is set to False.

    :param numpy array image: Array of numerical values

    :return numpy array data_grid: Array of boolean values
    """
    data_grid = np.empty([3, 3])
    size_x = round(image.shape[0]/data_grid.shape[0])
    size_y = round(image.shape[1]/data_grid.shape[1])

    for m in range(3):
        for k in range(3):
            image_subset = image[m*size_x:(m+1)*size_x, k*size_y:(k+1)*size_y]
            data_grid[m][k] = test_pixel(image_subset)

    return data_grid



def validate_wms(url, layer_name, srs, bbox, result_array, service_version):
    """Fetch image for the corresponding layer and search for variation with
       the same parameters in both the image and the result produced by the tool.

    :param str url: First part of URL pointing to a particular service
    :param str layer_name: Name of the layer
    :param str srs: EPSG code of a coordinate system
    :param list bbox: Bounding box as specified in the service metadata
    :param numpy array result_array: Array of boolean values; result
                                    of executing the main part of the tool.
    :param str service_version: Number of correctly determined pixels
    :return numpy array real_data: Information on variation within grid areas
                                   in image fetched from the server.
    :return numpy array our_grid:  Information on variation within grid areas
                                   in raster produced by the tool.

    """
    if srs == "CRS:84":
        srs = "EPSG:4326"

    #TODO: properly deal with service_version == None
    if service_version is None:
        service_version = "1.3.0"
    if service_version == "1.3.0":
        req_url = "{}?VERSION={}&SERVICE=WMS&REQUEST=GetMap&LAYERS={}&STYLES=&CRS={}\
                   &BBOX={}&WIDTH=256&HEIGHT=256&FORMAT=image/png&EXCEPTIONS=XML"\
                   .format(url, service_version, layer_name, srs, bbox)
    elif service_version == "1.1.1":
        req_url = "{}?VERSION={}&SERVICE=WMS&REQUEST=GetMap&LAYERS={}&STYLES=&SRS={}\
                   &BBOX={}&WIDTH=256&HEIGHT=256&FORMAT=image/png&EXCEPTIONS=XML"\
                   .format(url, service_version, layer_name, srs, bbox)
    else:
        raise Exception("Unknown service_version {}".format(service_version))

    logging.info("URL used for validation: {}".format(req_url))

    image_response = requests.get(req_url)

    try:
        image = np.array(Image.open(io.BytesIO(image_response.content)))
    except:
        return None, None

    real_data = test_for_var(image).astype("uint8")

    our_grid = test_for_var(result_array).astype("uint8")
    logging.info("WMS validation: data fetched from server:\n {}".format(real_data))
    logging.info("WMS validation: our data:\n {}".format(our_grid))
    return real_data, our_grid

def validate_wfs(url, layer_name, srs, bbox, result_file,\
                 service_version, max_features_for_validation):
    """Fetch data for the corresponding layer and generate an array
       that maps the spatial extent of the data

    :param str url: First part of URL pointing to a particular service
    :param str layer_name: Name of the layer
    :param str srs: EPSG code of a coordinate system
    :param list bbox: Bounding box as specified in the service metadata
    :param numpy array result_array: Array of boolean values; result
                                    of executing the main part of the tool.
    :param str service_version: Number of correctly determined pixels
    :param string max_features_for_validation: If exceeded, validation is skipped

    :return numpy array real_data: Information on the location of data in layer
                                   fetched from the server.
    """

    wfs_drv = ogr.GetDriverByName('WFS')

    # get just the layer name (as opposed to a URL)
    layer_name = layer_name.split(":")[-1]

    # Speeds up querying WFS capabilities for services with alot of layers
    gdal.SetConfigOption('OGR_WFS_LOAD_MULTIPLE_LAYER_DEFN', 'NO')

    # Set config for paging. Works on WFS 2.0 services and WFS 1.0 and 1.1 with some other services.
    gdal.SetConfigOption('OGR_WFS_PAGING_ALLOWED', 'YES')
    gdal.SetConfigOption('OGR_WFS_PAGE_SIZE', '10000')

    # Fix for SSL connection errors
    gdal.SetConfigOption('GDAL_HTTP_UNSAFESSL', 'YES')

    # Open the webservice

    try_url = "https://geodata.nationaalgeoregister.nl/inspireadressen/v2/wfs?language=dut&SERVICE=WFS&VERSION=2.0.0&SRSNAME=urn:ogc:def:crs:EPSG::28992&BBOX=138857.59757060264,559646.0172022979,258777.14235332562,679565.5619850209"
    #TODO: use version -> if service_version is not None: ...
    req_url = "{}?service=wfs&version=2.0.0&srsName={}&BBOX={}".format(url, srs, bbox)
    logging.info("URL used for validation: {}".format('WFS:' + req_url))

    wfs_ds = wfs_drv.Open('WFS:' + req_url)
    if not wfs_ds:
        logging.error("Couldn't open connection to the server.")
        #raise Exception("Couldn't open connection to the server.")
        return None

    shapes = []

    # Get a specific layer
    layer = wfs_ds.GetLayerByName(layer_name)
    if not layer:
        logging.error("Couldn't find layer in service")
        return None

    feature_count = layer.GetFeatureCount()
    if  max_features_for_validation is not None:
        if feature_count > int(max_features_for_validation):
            logging.warning("Validation for layer {} skipped. there was too many features: {}"\
                            .format(layer.GetName(), layer.GetFeatureCount()))
            return None

    logging.info("Layer: {}, Features: {}".format(layer.GetName(), feature_count))

    # iterate over features

    logging.info("Start iteration through features.")

    feat = layer.GetNextFeature()
    count = 0

    while feat is not None:
        count += 1
        if feature_count > 5000:
            log_every = 1000
        else:
            log_every = 100
        if count % log_every == 0:
            logging.info("Feature: {}".format(count))
        geom = feat.GetGeometryRef().GetLinearGeometry()
        json_feat = geojson.loads(geom.ExportToJson())
        shapes.append(json_feat)

        feat = layer.GetNextFeature()

    feat = None

    # Close the connection
    wfs_ds = None
    logging.info("Iteration done. Creating validation.")
    if count == 0:
        logging.info("No features in the layer.")
        real_data = np.zeros_like(result_file.read(1))
    else:
        real_data = rasterio.features.rasterize(
            shapes,
            out_shape=result_file.shape,
            transform=result_file.transform,
            dtype='uint8'
        )

    return real_data



def validate(url, layer_name, srs, bbox, result_path, output_path, service_type, service_version,\
             max_features_for_validation, flip_features, data_bounds, service_number):

    """Fetch data for the corresponding layer and generate an array
       that maps the spatial extent of the data

    :param str url: First part of URL pointing to a particular service
    :param str layer_name: Name of the layer
    :param str srs: EPSG code of a coordinate system
    :param list bbox: Bounding box as specified in the service metadata
    :param str result_path: Path to raster file produced by the tool
    :param str output_path: Path to location where the validation raster will be written.
    :param str service_type: Type of service (WMS/WFS)
    :param str service_version: Number of correctly determined pixels
    :param string max_features_for_validation: If exceeded, validation is skipped
    :param boolean flip_features: If set to True, coordinate order must be flipped
                                  in the URL
    :param list data_bounds: Bounding box that encapsulates
                             area with data as determined by the tool
    :param str service_number: Type of service (WMS/WFS)


    :return int: 0 if validation run OK; -1 if it failed.


    """

    logging.info("validation starts at {}".format(datetime.datetime.now()))
    # Open the file to be validated
    file = rasterio.open(result_path)


    if flip_features:
        bbox = [bbox[1], bbox[0], bbox[3], bbox[2]]

    # change bbox from a list into a string, remove spaces and brackets
    bbox_str = ''.join(char for char in str(bbox) if char not in '[]() ')


    if service_type == 'WMS':

        real_data, result = validate_wms(url, layer_name, srs, bbox_str,\
                                         file.read(1), service_version)

    elif service_type == 'WFS':

        real_data, result = validate_wfs(url, layer_name, srs, bbox_str, file,\
                                         service_version, max_features_for_validation), file.read(1)

    if real_data is None:
        logging.warning("Validation not successful. *feeling embarassed*")
        return -1
    


    # Since result is binary, the comparison is 0 if a value was the same.
    # 1 if we got false positive and -1 (i.e. 255 in uint8) if we got false negative.
    comparison = result - real_data
    output = rasterio.open(
        output_path,
        'w',
        driver='GTiff',
        nodata=99,
        height=file.height,
        width=file.width,
        count=1,
        dtype='uint8',
        crs=file.crs,
        transform=file.transform
    )



    output.write(comparison, 1)
    output.close()
    logging.info("Statistics:")
    logging.info("This is the np.unique count: {}"\
                 .format(np.unique(comparison, return_counts=True)))
    pixels_count = np.size(comparison)
    correct_pixels = None
    false_neg_pixels = None
    false_pos_pixels = None
    unique_vals = np.unique(comparison, return_counts=True)
    for i in range(len(unique_vals[0])):
        if unique_vals[0][i] == 0:
            correct_pixels = unique_vals[1][i]
            logging.info("Correct: {}%".format(round(100*correct_pixels/pixels_count)))
        elif unique_vals[0][i] == 1:
            false_pos_pixels = unique_vals[1][i]
            logging.info("False positives: {}%".format(round(100*false_pos_pixels/pixels_count)))
        # this is supposed to be -1 but since uint8 is 0 to 255 it underflows and makes it 255
        elif unique_vals[0][i] == 255:
            false_neg_pixels = unique_vals[1][i]
            logging.info("False negatives: {}%".format(round(100*false_neg_pixels/pixels_count)))
        else:
            raise Exception("Unexpected values in the validation raster: {}"\
                            .format(unique_vals[0]))

    bbox_area_decrease = area_decrease(bbox, data_bounds)

    write_statistics(output_path, service_number, layer_name, pixels_count, correct_pixels,\
                     false_pos_pixels, false_neg_pixels, bbox_area_decrease)


    return 0
