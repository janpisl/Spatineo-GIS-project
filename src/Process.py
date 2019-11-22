import pdb
import configparser
import argparse

import logging
# logging levels = DEBUG, INFO, WARNING, ERROR, CRITICAL
import datetime
logging.basicConfig(filename="../../output_data/logs/" + datetime.datetime.now().strftime("%d.%b_%Y_%H_%M_%S") + '.log', level=logging.INFO)

from Algorithm import Algorithm
from Validate import validate
from InputData import InputData
from ResultData import ResultData

class Process():

	def __init__(self, cfg):
		response_file_path = cfg.get('data', 'response_file')
		capabilities_path = cfg.get('data', 'get_capabilities')
		self.output_dir = cfg.get('data', 'output_dir')

		file = response_file_path.split('/')[-1].split('.')[0]

		self.input_data = InputData(response_file_path, capabilities_path)

		self.layer_name = self.input_data.get_layer_name()
		self.layer_bbox = self.input_data.bbox
		self.service_type = self.input_data.get_service_type()

		self.result = ResultData(self.input_data.crs, self.layer_bbox, self.output_dir)
		self.raster = self.result.create_empty_raster('tmp.tif')
		#		self.coarse_raster = self.result.create_empty_raster('tmp.tif', resolution = "coarse")

		self.features = self.input_data.get_bboxes_as_geojson()
		self.url = self.input_data.request_url
		self.service_version = self.input_data.service_version
		try:
			self.max_features_for_validation = cfg.get('other', 'max_features_for_validation')
		except:
			self.max_features_for_validation = None

		try:
			self.output_raster_path = cfg.get('data', 'raster_output_path')
			self.bin_raster_path = cfg.get('data', 'binary_raster_output_path')
			self.val_raster_output_path = cfg.get('data', 'validation_raster_output_path')
		except:
			self.output_raster_path = self.output_dir + file + ".tif"
			self.bin_raster_path = self.output_dir + "bin_" + file + ".tif"
			self.val_raster_output_path = self.output_dir + "val_" + file + ".tif"

	def run_algorithm(self):

		a = Algorithm(self.raster, self.input_data, self.service_type, self.result)

		return a.solve(self.features, self.output_raster_path, self.bin_raster_path)


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
	validate(process.url, process.layer_name, process.input_data.crs.name, 
				process.layer_bbox, process.bin_raster_path, process.val_raster_output_path, 
				process.service_type, process.service_version, process.max_features_for_validation)
