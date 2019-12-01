"""algorithm.py

Functions related to processing input data.

"""

import math
import logging
import datetime
from geojson import Polygon, Feature, FeatureCollection

import xml.etree.ElementTree as ET
from Projection import change_bbox_axis_order, is_first_axis_east

# logging levels = DEBUG, INFO, WARNING, ERROR, CRITICAL
logging.basicConfig(filename="../../output_data/logs/" \
                    + datetime.datetime.now().strftime("%d.%b_%Y_%H_%M_%S") \
                    + '.log', level=logging.INFO)


def get_resolution(crs, cfg_resolution):
    """Convert resolution from configuration if crs unit is degrees

    :param CRS object crs: Contains information related to CRS
    :param int cfg_resolution: Resolution in meters set in the configuration

    :return int resolution: Resolution on correct unit
    """

    unit = crs.axis_info[0].unit_name
    if unit == 'metre':
        resolution = cfg_resolution
    elif unit == 'degree':
        resolution = cfg_resolution/100000
    else:
        raise Exception("The used coordinate unit ({}) is not configured. \
                        Cannot continue.".format(unit))

    return resolution


def get_service_type(path_to_capabl):
    """Parse Get_Capabilities document and find out the type of service

    :param str path_to_capabl: Path to Get_Capabilities document

    :return str service: Either 'WMS' or 'WFS'
    """

    root = ET.parse(path_to_capabl).getroot()
    service = None

    if "wms" in root.tag.lower():
        service = 'WMS'

    elif "wfs" in root.tag.lower():
        service = 'WFS'

    else:
        for element in root:
            for child in element:
                if "wms" in child.text.lower():
                    return 'WMS'
                elif "wfs" in child.text.lower():
                    return "WFS"

    if service is None:
        raise Exception("Couldn't retrieve service type from {}".format(root.tag))

    return service

def get_bboxes_as_geojson(layer_bbox, responses, crs, sample=False, flip_features=False):
    """Convert response file to geojson geometries.

    imageAnalysisResult is included to the geojson features.

    :param tuple layer_bbox: Bounding box as specified in the service metadata
    :param list responses: list of original responses
    :param CRS object crs: Contains information related to CRS
    :param boolean sample: only get every tenth element; defaults to False
    :param boolean flip_features: flip coordinate order; defaults to False

    :return list: Geojson elements
    """
    features = []

    if not is_first_axis_east(crs):
        layer_bbox = change_bbox_axis_order(layer_bbox)


    unit = crs.axis_info[0].unit_name
    if unit == 'metre' or 'meter':
        extent = [math.floor(layer_bbox[0]), math.floor(layer_bbox[1]),
                  math.ceil(layer_bbox[2]), math.ceil(layer_bbox[3])]
    elif unit == "degree":
        c = 100000
        extent = [math.floor(layer_bbox[0]*c)/c, math.floor(layer_bbox[1]*c)/c,
                  math.ceil(layer_bbox[2]*c)/c, math.ceil(layer_bbox[3]*c)/c]
    else:
        raise Exception("Unknown unit type '{}'. Error in get_bboxes_as_geojson".format(unit))

    invalid_request_count = 0
    bbox_out_count = 0

    count = 0

    '''
    coords_min = [float('inf'), float('inf')]
    coords_max = [float('-inf'), float('-inf')]
    '''

    logging.info("Creating geojson objects.")
    for res in responses:
        count += 1
        # If in sampling mode, only process 1 out of 10 features
        if sample is True:
            if count % 10 != 0:
                continue

        if count % 1000 == 0:
            logging.debug("Result no. {}".format(count))

        # Filter out invalid test results
        if ('imageAnalysisResult' not in res.keys() or 'testResult' not in res.keys()
                or res['testResult'] != 0):
            invalid_request_count += 1
            continue

        # Convert bbox as a list.
        bbox = list(map(float, res['bBox'].split(',')))


        inside = [
            bbox[0] >= extent[0],
            bbox[1] >= extent[1],
            bbox[2] <= extent[2],
            bbox[3] <= extent[3],
        ]

        # Filter out requests out of the interest area
        if not all(inside):
            bbox_out_count += 1
            continue

        '''
        if bbox_out_count == 0:
            for i in range(len(coords_min)):
                if bbox[i] < coords_min[i]:
                    coords_min[i] = bbox[i]
            for i in range(len(coords_max)):
                if bbox[i + len(coords_max)] > coords_max[i]:
                    coords_max[i] = bbox[i  + len(coords_max)]
        '''


        # Create a closed Polygon following the edges of the bbox.
        if flip_features is True:
            g = Polygon([[(bbox[1], bbox[0]), (bbox[3], bbox[0]),
                          (bbox[3], bbox[2]), (bbox[1], bbox[2]), (bbox[1], bbox[0])]])
        else:
            g = Polygon([[(bbox[0], bbox[1]), (bbox[0], bbox[3]),
                          (bbox[2], bbox[3]), (bbox[2], bbox[1]), (bbox[0], bbox[1])]])


        # Save other data
        props = {
            'imageAnalysisResult': res['imageAnalysisResult'],
            'testResult': res['testResult'],
            'requestTime': res['requestTime']
        }
        feat = Feature(geometry=g, properties=props)

        features.append(feat)

    if invalid_request_count > 0:
        logging.info("Filtered {} requests away due to failed request."
                     .format(invalid_request_count))

    if bbox_out_count > 0:
        logging.info("Filtered {} requests away because request bbox \
                      was not completely within layer bbox".format(bbox_out_count))

    '''else:
        self.bbox = coords_min + coords_max
        logging.info("Bounding box set to the extent of all requests to {}".format(self.bbox))'''

    features_flipped = False

    if len(features) == 0:
        if flip_features:
            raise Exception("Coordinate order problem!")
        logging.warning("No features found within layer bounding box. \
                        Trying again with different axis order.")
        features, features_flipped = get_bboxes_as_geojson(layer_bbox, responses, crs,
                                                           sample=sample, flip_features=True)
        features_flipped = True

    feat_c = FeatureCollection(features)

    return feat_c, features_flipped
