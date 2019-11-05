'''- project task
	- when you create an empty raster, how do you set its bbox (georeferencing); generally, learn how to use rasterio with coordinates as opposed to pixel indices 
	- from json, get CRS, 
	- from xml, get bbox of the layer
	- how to set width and height? Depends on resolution; that is something we decide once for the entire project? For now, yes. Then:
		- width, height = bbox(x, y)/resolution
			- if we want res 1px = 2*2km and the bbox is 1000*1000km,
				then its 1000/2 for both width and height
		- but perhaps in the future, width and height could be fixed and resolution dynamic, because if the bbox is smaller, it is reasonable to operate with smaller pixels

'''

import rasterio
import numpy as np
from math import floor, ceil
import xml.etree.ElementTree as ET
import pdb
import json
import configparser
import argparse
import utm

from Algorithm import Algorithm
from Validate import validate
from Projection import Projection
from Capabilities import Capabilities
from ResultData import ResultData

class Process():

	def __init__(self, cfg):
		response_file_path = cfg.get('data', 'response_file')
		capabilities_path = cfg.get('data', 'get_capabilities')
		
		self.get_capabilities = Capabilities(capabilities_path)

		self.requests = self.load_requests(response_file_path)
		crs_name = self.requests['layerKey']['crs']
		self.crs = Projection(crs_name)
		self.layer_name = self.requests['layerKey']['layerName']

		self.layer_bbox = self.get_capabilities.get_layer_bbox(self.layer_name, self.crs)

		self.result = ResultData(self.crs, self.layer_bbox, 1000, '../../')
		self.raster = self.result.create_empty_raster('tmp.tif')
		# not tested, there might be some problems
		self.url = self.requests['results'][0]['url'].split("?")[0]
		try: 
			self.output_raster_path = cfg.get('data', 'raster_output_path')
		except:
			self.output_raster_path = '../../out.tif'
		try:
			self.bin_raster_path = cfg.get('data', 'binary_raster_output_path')
		except:
			self.bin_raster_path = '../../bin_out.tif'



	def load_requests(self, path):
		with open(path) as source:
			requests = json.load(source)

		return requests


	def run_algorithm(self):

		a = Algorithm(self.raster, self.requests, self.get_capabilities.service_type)

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
	validate(process.url, process.layer_name, process.crs.name, process.layer_bbox, process.bin_raster_path, "../../validation21764.tif")
