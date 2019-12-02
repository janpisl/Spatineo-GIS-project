"""process.py

For a json-like file with responses of requests and
a Get_Capabilities document for a corresponding service,
perform an analysis to find the location of data of that
service. Store the location as a geopackage. Execute
validation to find out how the result corresponds
to the actual spatial distribution of service data.
Requires a configuration file.

How to run:

        $ python3 process.py process.ini

"""

import logging
import configparser
import argparse
import datetime
import pdb
import json

from Algorithm import solve
from Validate import validate
from InputData import get_resolution, get_service_type, get_bboxes_as_geojson
from ResultData import create_empty_raster, convert_to_vector_format, shrink_bbox
from Projection import CRS, solve_first_axis_direction
from Capabilities import get_layer_bbox



logging.basicConfig(filename="../../output_data/logs/" \
                    + datetime.datetime.now().strftime("%d.%b_%Y_%H_%M_%S") \
                    + '.log', level=logging.INFO)



class Process(object):
    """Set up environment for analysis and perform it."""

    def __init__(self, cfg):
        """ Parse configuration, retrieve data neccessary for
        analysis from input files and generate data structures that
        will be used in the analysis. """

        response_file_path = cfg.get('data', 'response_file')
        capabilities_path = cfg.get('data', 'get_capabilities')
        self.output_dir = cfg.get('data', 'output_dir')
        self.service = capabilities_path.split('/')[-1].split('.')[0]
        
        file = response_file_path.split('/')[-1].split('.')[0]

        try:
            self.output_raster_path = cfg.get('data', 'raster_output_pathsd')
        except (configparser.NoOptionError, configparser.NoSectionError):
            self.output_raster_path = self.output_dir + file + ".tif"
        try:
            self.bin_raster_path = cfg.get('data', 'binary_raster_output_path')
        except (configparser.NoOptionError, configparser.NoSectionError):
            self.bin_raster_path = self.output_dir + "bin_" + file + ".tif"
        try:
            self.val_raster_output_path = cfg.get('data', 'validation_raster_output_path')
        except (configparser.NoOptionError, configparser.NoSectionError):
            self.val_raster_output_path = self.output_dir + "val_" + file + ".tif"
        try:
            self.max_features_for_validation = int(cfg.get('other', 'max_features_for_validation'))
        except (configparser.NoOptionError, configparser.NoSectionError):
            self.max_features_for_validation = None

        with open(response_file_path) as source:
            self.responses_file = json.load(source)

        self.max_raster_size = int(cfg.get('other', 'max_raster_size'))

        self.responses_header = self.responses_file['layerKey']
        self.responses = self.responses_file['results']

        self.layer_name = self.responses_header['layerName']

        self.service_type = get_service_type(capabilities_path)
        try:
            self.service_version = self.responses[0]['url'].split("VERSION=")[1].split("&")[0]
        except:
            self.service_version = None

        input_crs = self.responses_header['crs']
        input_axis_dir = cfg.get('input', 'first_axis_direction')

        if input_axis_dir not in ('east', 'north', 'epsg'):
            input_axis_dir = solve_first_axis_direction(self.service_type,
                                                        self.service_version, input_crs)
        self.crs = CRS(self.responses_header['crs'], input_axis_dir)

        output_crs = cfg.get('result', 'output_crs')
        output_axis_dir = cfg.get('result', 'first_axis_direction')
        self.output_crs = CRS(output_crs, output_axis_dir)

        cfg_resolution = int(cfg.get('result', 'resolution'))
        self.resolution = get_resolution(self.crs, cfg_resolution)

        self.url = self.responses[0]['url'].split("?")[0]


        self.layer_bbox = get_layer_bbox(capabilities_path, self.layer_name,
                                         self.crs, self.service_type)

        '''
        #uses only 1/10 for bbox shrinking
        #self.features_sample, self.flip_features = \
            get_bboxes_as_geojson(self.layer_bbox, self.responses, self.crs, sample = False)

        self.coarse_raster = create_empty_raster(self.output_dir + "/" + "tmp_coarse.tif",
            self.crs, self.layer_bbox, resolution="coarse", max_raster_size=self.max_raster_size)

        self.bbox = shrink_bbox(self.coarse_raster, self.features_sample)
        logging.info("layer bbox: {}".format(self.layer_bbox))
        logging.info("shrinked bbox: {}".format(self.bbox))
        # If shrinked bbox isn't smaller than original, use original
        if (self.layer_bbox[3]-self.layer_bbox[1]) <= (self.bbox[3]-self.bbox[1]) \
           and (self.layer_bbox[2]-self.layer_bbox[0]) <= (self.bbox[2]-self.bbox[0]):
            self.bbox = self.layer_bbox
        else:
            logging.info("Bounding box based on spatial distribution of requests is being used.")
        ## END
        '''
        self.bbox = self.layer_bbox

        self.features, self.flip_features = get_bboxes_as_geojson(self.bbox,
                                                                  self.responses, self.crs)
        self.raster, self.resolution = create_empty_raster(self.output_dir + "/" + "tmp.tif", \
                                                           self.crs, self.bbox, self.resolution, \
                                                           max_raster_size=self.max_raster_size)



    def run_algorithm(self):

        solve(self.features, self.raster, self.bin_raster_path)
        self.data_bounds = convert_to_vector_format(self.crs, self.output_dir, self.resolution,
                                                    self.bin_raster_path, self.output_crs,
                                                    self.url, self.layer_name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument("path_to_config", help="Path to the file containing configuration.")
    args = parser.parse_args()

    config = configparser.ConfigParser()
    data = config.read(args.path_to_config)
    if len(data) == 0:
        raise Exception("Configuration file not found.")

    process = Process(config)

    process.run_algorithm()

    # validation of the result.
    validate(process.url, process.layer_name, process.crs.crs_code,
             process.layer_bbox, process.bin_raster_path,
             process.val_raster_output_path, process.service_type,
             process.service_version, process.max_features_for_validation,
             process.flip_features, process.data_bounds, process.service)
