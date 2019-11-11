import configparser
import argparse
import pdb
import glob

from Process import Process


def run_batch(cfg):
[data]
response_file
	directory = cfg.get('data', 'response_file')
	for file in glob.glob('./*.json'):
		cfg.set()

	process = Process(config)
	process.run_algorithm()
	# validation of the result. 
	validate(process.url, process.layer_name, process.crs.name, process.layer_bbox, process.bin_raster_path, "../../validation21764.tif")


if __name__ == '__main__':
	pdb.set_trace()
	parser = argparse.ArgumentParser()
	parser.add_argument("path_to_config", help="Path to the file containing configuration.")
	args = parser.parse_args()

	config = configparser.ConfigParser()
	data = config.read(args.path_to_config)
	if len(data) == 0:
		raise Exception("Configuration file not found.")
	
	run_batch(config)

