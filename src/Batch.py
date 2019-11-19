import configparser
import argparse
import pdb
import glob
import logging

from Process import Process
from pathlib import Path
from Validate import validate

import datetime
logging.basicConfig(filename="../../output_data/logs/" + datetime.datetime.now().strftime("%d.%b_%Y_%H_%M_%S") + '.log', level=logging.INFO)


def run_batch(cfg):

	directory = cfg.get('data', 'response_file')
	get_capabilities_docs = cfg.get('data', 'get_capabilities')
	output_dir = cfg.get('data', 'output_dir')


	for file_path in glob.glob(directory + '*.json'):
		file = Path(file_path).stem
		logging.info("file {} begins".format(file))

		config = configparser.ConfigParser()
		config.add_section('data')

		config.set('data', 'response_file', file_path)
		config.set('data', 'get_capabilities', get_capabilities_docs + file.split("_")[0] + ".xml")
		config.set('data', 'raster_output_path', output_dir + file + ".tif")

		config.set('data', 'output_dir', output_dir)
		config.set('data', 'raster_output_path', output_dir + file + ".tif")
		config.set('data', 'binary_raster_output_path', output_dir + "bin_" + file + ".tif")
		config.set('data', 'validation_raster_output_path', output_dir + "val_" + file + ".tif")

		process = Process(config)
		process.run_algorithm()

		# validation of the result. 
		validate(process.url, process.layer_name, process.input_data.crs.name, 
					process.layer_bbox, process.bin_raster_path, process.val_raster_output_path, 
					process.service_type, process.service_version)

		logging.info("file {} done \n \n".format(file))


if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument("path_to_config", help="Path to the file containing configuration.")
	args = parser.parse_args()

	config = configparser.ConfigParser()
	data = config.read(args.path_to_config)
	if len(data) == 0:
		raise Exception("Configuration file not found.")
	
	run_batch(config)

