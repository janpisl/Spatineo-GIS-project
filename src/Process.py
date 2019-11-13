import pdb
import configparser
import argparse

import logging
# logging levels = DEBUG, INFO, WARNING, ERROR, CRITICAL
import datetime
logging.basicConfig(filename=datetime.datetime.now().strftime("%d.%b_%Y_%H_%M_%S") + '.log', level=logging.INFO)

from Algorithm import Algorithm
from Validate import validate
from InputData import InputData
from ResultData import ResultData

class Process():

	def __init__(self, cfg):
		response_file_path = cfg.get('data', 'response_file')
		capabilities_path = cfg.get('data', 'get_capabilities')
		
		self.input_data = InputData(response_file_path, capabilities_path)

		self.layer_name = self.input_data.get_layer_name()
		self.layer_bbox = self.input_data.get_capabilities_bbox()
		self.service_type = self.input_data.get_service_type()

		self.result = ResultData(self.input_data.crs, self.layer_bbox, '../../')
		self.raster = self.result.create_empty_raster('tmp.tif')

		# not tested, there might be some problems
		self.url = self.input_data.get_request_url()
		try: 
			self.output_raster_path = cfg.get('data', 'raster_output_path')
		except:
			self.output_raster_path = '../../out.tif'
		try:
			self.bin_raster_path = cfg.get('data', 'binary_raster_output_path')
		except:
			self.bin_raster_path = '../../bin_out.tif'

	def run_algorithm(self):

		a = Algorithm(self.raster, self.input_data, self.service_type)

		return a.solve(self.output_raster_path, self.bin_raster_path)


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
	validate(process.url, process.layer_name, process.input_data.crs.name, process.layer_bbox, process.bin_raster_path, "../../validation21764.tif", process.service_type)
