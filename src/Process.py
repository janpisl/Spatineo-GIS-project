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
#pdb.set_trace()


class Process():

	def __init__(self, cfg):
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

		'''TODO: implement this function to actually look in the xml, i.e.
				 find the appropriate child by layer_name (so where someChildNode.nodeValue == layer_name,
				 then find the bbox values for our crs (bounding box tag where CRS = crs)
				 This is what we want:
		 		<BoundingBox CRS="EPSG:3067" minx="192328.204900" miny="6639377.660400" maxx="861781.306600" maxy="7822120.847100"/>

		for a start, this is how to parse an xml:
		'''
		tree = ET.parse(self.get_capabilities)
		root = tree.getroot()
		for child in root:
			for child1 in child:

				print(child1.tag)
				#print(child1.tag.split('}', 1)[1])
		
		# Quickfix before we implement this
		bbox = [192328.204900, 6639377.660400, 861781.306600, 7822120.847100]

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

		# Calculate height and width. 
		# Note, the meaning of x and y changes between crs! Now, width = x, height = y
		width = maxx - minx
		height = maxy - miny
		data = np.zeros(shape=(height, width))

		transform = rasterio.transform.from_origin(minx, maxy, 1000, 1000)

		# Create new dataset
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

		dataset.write(data, 1)
		dataset.close()

		return output_name




#TODO: access req_layer_name in the xml; get the bbox; create a raster;


if __name__ == '__main__':
	config = configparser.ConfigParser()
	#TODO: give ini file as an argument
	cfg = config.read("process.ini")
	process = Process(cfg)



