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
# Renee test commit

import rasterio
import numpy as np
from math import floor, ceil
import xml.etree.ElementTree as ET
import pdb
import json
import configparser

#pdb.set_trace()


class Process():

	def __init__(self, cfg):
		#self.response_file_path = 'converted_example_service.txt'
		self.response_file_path = cfg.get('data', 'response_file')
		self.get_capabilities = cfg.get('data', 'get_capabilities')
		self.requests = self.load_requests(self.response_file_path)
		self.crs = self.requests['layerKey']['crs']
		self.layer_name = self.requests['layerKey']['layerName']		
		self.layer_bbox = self.get_layer_bbox(self.layer_name, self.crs)

	def load_requests(self, path):
		with open(path) as source:
			requests = json.load(source)

		return requests


	def get_layer_bbox(self, layer_name, crs):
		''' Here comes the short description what the method do.

			args:
				layer_name: Layer name of the service
				crs: the coordinate reference system (EPSG code)
			returns:
				bbox: bounding box (array) of the service
		'''

		tree = ET.parse(self.get_capabilities)
		root = tree.getroot()

		layer = False
		for element in root.findall('{http://www.opengis.net/wms}Capability/{http://www.opengis.net/wms}Layer/{http://www.opengis.net/wms}Layer/{http://www.opengis.net/wms}Layer/'):
			
			if element.text == self.layer_name:
				layer = True

			if element.tag == '{http://www.opengis.net/wms}BoundingBox' and element.attrib['CRS'] == self.crs and layer:
				bbox = [element.attrib['minx'], element.attrib['miny'], element.attrib['maxx'], element.attrib['maxy']]

				for item in range(len(bbox)):
					bbox[item] = float(bbox[item])
		#bbox = [192328.204900, 6639377.660400, 861781.306600, 7822120.847100]

		return bbox


	def create_empty_raster(self, output_name, height, width, crs, bbox, driver='GTiff'):
		''' This function creates an empty raster file with the provided parametres.
		args:
			output_name: the path where the dataset will be created
			height: the height of the new file in pixels
			width: the width of the new file in pixels
			crs: coordinate reference system which will be used, (e.g. EPSG:3067)
			bbox: bounding box [minx, miny, maxx, maxy]
			driver: GDAL raster driver to create datasets
		returns: the path where the dataset was created (the same as output_name)
		'''
		# TODO: Since we have to update the dataset reguraly, it would be good
		# to create a separated helper class for raster data handling!

		# Round up or down to the nearest kilometer.
		# Assume now that the unit is a meter!
		minx = floor(bbox[0]/1000) * 1000
		miny = floor(bbox[1]/1000) * 1000
		maxx = ceil(bbox[2]/1000) * 1000
		maxy = ceil(bbox[3]/1000) * 1000

		# Calculate the scale
		# Note, the meaning of x and y changes between crs! Now, width = x, height = y. Make this more robust at some point.
		scalex = (maxx - minx) / width
		scaley = (maxy - miny) / height

		# This ties spatial coordinates and image coordinates together.
		transform = rasterio.transform.from_origin(minx, maxy, scalex, scaley)

		# Init raster with zeros.
		data = np.zeros(shape=(height, width))

		# Create new dataset file
		dataset = rasterio.open(
			output_name,
			'w', # Write mode
			driver=driver,
			height=height,
			width=width,
			count=1,
			dtype=str(data.dtype),
			crs=crs,
			transform=transform,
		)

		# Write numpy matrix to the dataset.
		dataset.write(data, 1)
		dataset.close()

		return output_name



if __name__ == '__main__':
	config = configparser.ConfigParser()
	#TODO: give ini file as an argument
	config.read("/home/jan/Documents/Aalto/Spatineo_Project/Spatineo-GIS-project/sample_data/process.ini")

	process = Process(config)
	
