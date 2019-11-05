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

		self.raster = self.create_empty_raster('../../tmp.tif')
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


	def create_empty_raster(self, output_name, resolution=1000, driver='GTiff'):
		''' This function creates an empty raster file with the provided parametres.
		args:
			output_name: the path where the dataset will be created
			driver: GDAL raster driver to create datasets
		returns: the path where the dataset was created (the same as output_name)
		'''
		# TODO: Since we have to update the dataset reguraly, it would be good
		# to create a separated helper class for raster data handling!

		# Check if crs is in degrees
		if not self.crs.is_projected:
		
			#	_min = utm.from_latlon(self.layer_bbox[1], self.layer_bbox[0])
			#	_max = utm.from_latlon(self.layer_bbox[3], self.layer_bbox[2])
			#	bbox = [_min[0], _min[1], _max[0], _max[1]]
			#elif crs_in_degrees[1] in self.crs:
			_min = utm.from_latlon(self.layer_bbox[0], self.layer_bbox[1])
			#TODO: this needs to be converted into the same crs as _min
			_max = utm.from_latlon(self.layer_bbox[2], self.layer_bbox[3])
			bbox = [_min[0], _min[1], _max[0], _max[1]]

		else:
			bbox = self.layer_bbox

		# Round up or down to the nearest kilometer.
		# Assume now that the unit is a meter!
		if not self.crs.coordinate_unit().lower() == 'metre':
			raise Exception("Coordinate unit not metre. Implementation is missing for other units.")
		
		minx = floor(bbox[0]/resolution) * resolution
		miny = floor(bbox[1]/resolution) * resolution
		maxx = ceil(bbox[2]/resolution) * resolution
		maxy = ceil(bbox[3]/resolution) * resolution

		# Calculate the scale
		# "Normal" case
		if not self.crs.input_ne_axis_order:
			width = int((maxx - minx) / resolution)
			height = int((maxy - miny) / resolution)
			transform = rasterio.transform.from_origin(minx, maxy, resolution, resolution)
		# If north axis is given first.
		else:
			height = int((maxx - minx) / resolution)
			width = int((maxy - miny) / resolution)
			transform = rasterio.transform.from_origin(maxy, minx, resolution, resolution)

		# Init raster with zeros.
		data = np.zeros(shape=(height, width))

		# Create new dataset file
		dataset = rasterio.open(
			output_name,
			'w', # Write mode
			driver=driver,
			# the no data value must be set because, the actual value doesnt matter AFAIK
			nodata = -99,
			height=height,
			width=width,
			count=1,
			dtype=str(data.dtype),
			crs=self.crs.name,
			transform=transform,
		)

		# Write numpy matrix to the dataset.
		dataset.write(data, 1)
		dataset.close()

		return output_name

	#TODO: actually get WMS/WFS value from get_capabilities or json
	def run_algorithm(self):

		a = Algorithm(self.raster, self.requests, "WFS")

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
