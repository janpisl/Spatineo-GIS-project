"""result_data.py

Includes functions for creating an empty raster with
given parameters and for converting raster data into
vector and saving it to disk.


"""

import datetime
import logging
from math import floor, ceil, log10
import numpy as np
import scipy.ndimage

from shapely.geometry import shape, mapping, MultiPolygon
# TODO: check naming if it overlapping or not to variables of this file?
from shapely.ops import transform as shapely_transform
import rasterio
from rasterio.features import shapes
import fiona
import fiona.crs
from pyproj import Transformer

from Projection import is_first_axis_east
from Algorithm import compute_density_rasters

# logging levels = DEBUG, INFO, WARNING, ERROR, CRITICAL
logging.basicConfig(filename="../../output_data/logs/" \
                    + datetime.datetime.now().strftime("%d.%b_%Y_%H_%M_%S") \
                    + '.log', level=logging.INFO)



def get_raster_shapes(resolution, bbox, crs):
    """Get attributes neccessary for raster creation

    :param int resolution: Default resolution of the raster
    :param list bbox: Spatial extent of the data as specified in the layer metadata
    :param CRS object crs: Contains information related to CRS

    :return:
        int height: Height for the raster that is to be created
        int width: Height for the raster that is to be created
        int transform: Affine transformation matrix
    """

    # Some helper functions
    def round_down(val):
        return floor(val / resolution) * resolution
    def round_up(val):
        return ceil(val / resolution) * resolution
    # Round up or down to regarding to the resolution value.
    minx = round_down(bbox[0])
    miny = round_down(bbox[1])
    maxx = round_up(bbox[2])
    maxy = round_up(bbox[3])

    # Calculate the scale
    # "Normal" case
    if is_first_axis_east(crs):
        width = round((maxx - minx) / resolution)
        height = round((maxy - miny) / resolution)
        transform = rasterio.transform.from_origin(minx, maxy, resolution, resolution)
    # If north axis is given first.
    else:
        height = round((maxx - minx) / resolution)
        width = round((maxy - miny) / resolution)
        transform = rasterio.transform.from_origin(miny, maxx, resolution, resolution)


    return height, width, transform

def create_empty_raster(output_path, crs, bbox, resolution, max_raster_size, driver='GTiff'):
    """Create an empty raster file with the provided parametres.

    :param str output_path: Path where the dataset is to be created
    :param CRS object crs: Contains information related to CRS
    :param list bbox: Spatial extent of the data as specified in the layer metadata
    :param int resolution: Default resolution of the raster
    :param int max_raster_size: Maximum number of pixels for the raster
    :param str driver: GDAL raster driver to create datasets

    :return:
        str output_path: Path where the dataset was created
        int resolution: Pixel size of the raster
    """

    skip_logging = False
    COARSE_RES = 50

    if resolution == "coarse":
        avg_dist = (abs(bbox[0] - bbox[2]) + abs(bbox[1] - bbox[3]))/2
        resolution = avg_dist/COARSE_RES
        skip_logging = True

    while True:
        height, width, transform = get_raster_shapes(resolution, bbox, crs)
        if height*width <= max_raster_size:
            break
        else:
            resolution = resolution*2

    if not skip_logging:
        logging.info("Resolution with which the analysis will be done set to: '{}' "
                     .format(resolution))
        logging.info("Raster size set to {}, {}".format(height, width))
    # Init raster with zeros.
    data = np.zeros(shape=(height, width))

    # Create new dataset file
    dataset = rasterio.open(
        output_path,
        'w', # Write mode
        driver=driver,
        nodata=-99,
        height=height,
        width=width,
        count=1,
        dtype=str(data.dtype),
        crs=crs.crs_code,
        transform=transform,
    )

    # Write numpy matrix to the dataset.
    dataset.write(data, 1)
    dataset.close()

    return output_path, resolution


def convert_to_vector_format(crs, output_dir, resolution,
                             input_file, output_crs, url, layer_name):
    """Create layer name based on the raster file name

    :param str output_dir: Path leading to directory where outputs are created
    :param int resolution: Default resolution of the raster
    :param str input_file: Path to the binary raster created in algorithm.solve
    :param str output_crs: Coordinate system to be used for output file
    :param str url: URL that is added as an attribute
    :param str layer_name: layer_name that is added as an attribute

    :return tuple: spatial extent of the data
    """

    dst_layername = input_file.split('/')[-1].split('.')[0]

    with rasterio.open(input_file, driver='GTiff', mode='r') as src:
        image = src.read(1)

        # Smooth output with median filter.
        # TODO: Move experimental this factor to config?
        smooth_kernel_size = round(min(image.shape)/30)
        if smooth_kernel_size > 1:
            pixels = scipy.ndimage.median_filter(image, (smooth_kernel_size, smooth_kernel_size),
                                                 mode='constant')
        else:
            pixels = image

        # Mask value is 1, which means data
        mask = pixels == 1

        # Tolerance for douglas peucker simplification
        tol = max(100 * log10(resolution), 0) # TODO: not work with degrees

        if crs != output_crs:
            tr = Transformer.from_crs(crs, output_crs,
                                      always_xy=is_first_axis_east(output_crs)).transform
        else:
            tr = None

        # Transformation and convertion from shapely shape to geojson-like object for fiona.
        feats = []
        feats_original_crs = []
        for (s, v) in shapes(pixels, mask=mask, transform=src.transform):
            shp = shape(s).simplify(tol)
            feats_original_crs.append(shp)
            if tr:
                shp = shapely_transform(tr, shp)
            feats.append(shp)


        feature = MultiPolygon(feats)
        result = {'geometry': mapping(feature), 'properties':
                  {'resolution': resolution, 'url': url, 'layer_name': layer_name}}



        results_gpkg = ({'geometry': mapping(f), 'properties': {}} for f in feats)


    with fiona.open(
        output_dir + dst_layername + ".geojson", 'w',
        driver="GeoJSON",
        crs=fiona.crs.from_string(output_crs.to_proj4()) if output_crs else src.crs,
        schema={'geometry': feature.type, 'properties':
                {'resolution': 'int', 'url': 'str', 'layer_name': 'str'}},
        VALIDATE_OPEN_OPTIONS=False) as dst:


        with fiona.open(
            output_dir + dst_layername + ".gpkg", 'w',
            driver="GPKG",
            crs=fiona.crs.from_string(output_crs.to_proj4()) if output_crs else src.crs,
            schema={'geometry': 'Polygon', 'properties': {}}) as gpkg_dst:


            if len(feats) > 0:
                dst.write(result)
                gpkg_dst.writerecords(results_gpkg)


    return MultiPolygon(feats_original_crs).bounds


def shrink_bbox(coarse_raster, features):
    eval_raster, norm_raster, request_counter = \
        compute_density_rasters(features, coarse_raster)

    bin_norm_raster = norm_raster > np.max(norm_raster)/1000

    open_coarse_raster = rasterio.open(coarse_raster)

    datapixel_indices = np.argwhere(bin_norm_raster is True)

    min_coords = open_coarse_raster.xy(np.max(datapixel_indices[:, 1]),
                                       np.min(datapixel_indices[:, 2]), offset='ll')
    max_coords = open_coarse_raster.xy(np.min(datapixel_indices[:, 1]),
                                       np.max(datapixel_indices[:, 2]), offset='ur')

    return [int(round(coord)) for coord in min_coords + max_coords]
