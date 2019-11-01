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
from pyproj import Proj, transform

class Process():

	def __init__(self, cfg):
		self.response_file_path = cfg.get('data', 'response_file')
		self.get_capabilities = cfg.get('data', 'get_capabilities')
		self.requests = self.load_requests(self.response_file_path)
		self.service = self.get_service(self.get_capabilities)
		self.crs = self.requests[0]['layerKey']['crs']
		self.layer_name = self.requests[0]['layerKey']['layerName']
		self.layer_bbox = self.get_layer_bbox(self.layer_name, self.crs, self.service)

		self.raster = self.create_empty_raster('../../tmp.tif')
		# not tested, there might be some problems
		self.url = self.requests[0]['results'][0]['url'].split("?")[0]
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


	def get_service(self, get_capabilities):
		tree = ET.parse(self.get_capabilities)
		root = tree.getroot()

		if "wms" in root.tag.lower():
			service_name = 'WMS'
		if "wfs" in root.tag.lower():
			service_name = 'WFS'
		else:
			raise Exception("Couldn't retrieve service type from {}".format(root.tag))

		return service_name


	def get_layer_bbox(self, layer_name, crs, service):
		''' The fuction parses the GetCapabilities XML document retrieved in _init_ function in order to search for a 'global' bbox to use. 
			It retrieves the bbox from the GetCapabilties document by finding the tag of the current request where it finds the bbox with correct CRS. 
			 

			args:
				layer_name: Layer name of the service
				crs: the coordinate reference system (EPSG code)
				service: service name (WMS/WFS)
			returns:
				bbox: bounding box (array) of the service
		'''
		# TODO: It must be able to do both WMS and WFS as well as work with different types of XML document setups.
		epsg_code = int(self.requests[0]['layerKey']['crs'].split(':')[-1])  #retrieves epsg code

		if self.service == 'WMS':
			# WMS solution
			# init
			bbox = None
			layer = False

			# parsing the XML document to the the root (setup) of the document
			tree = ET.parse(self.get_capabilities)
			root = tree.getroot()

			# searching the XML document for the tag with the correct request name
			for element in root.findall('{http://www.opengis.net/wms}Capability/{http://www.opengis.net/wms}Layer/{http://www.opengis.net/wms}Layer/{http://www.opengis.net/wms}Layer/'):
				# this is to ensure it doesn't search in other layers in case bbox is not found in the target layer
				# it is not 100% so if there are any problems remove it
				if (element.tag == '{http://www.opengis.net/wms}Name') and (element.text != self.layer_name):
					layer = False
				# change layer to true if the request is found
				if element.text == self.layer_name:
					layer = True

				# retrieve the bbox when the contraints are upheld
				if element.tag == '{http://www.opengis.net/wms}BoundingBox' and element.attrib['CRS'] == epsg_code and layer:
					bbox = [element.attrib['minx'], element.attrib['miny'], element.attrib['maxx'], element.attrib['maxy']]

					# change from strings to float
					for item in range(len(bbox)):
						bbox[item] = float(bbox[item])
					# this is to stop the search when bbox is found. if not here, bbox values get overwritten by values from other layers
					break

			#bbox = [192328.204900, 6639377.660400, 861781.306600, 7822120.847100]

			# throw exception if the bbox is not found
			if not bbox:
				raise Exception("Bounding box information not found for the layer.")

		elif self.service == 'WFS':

			# init
			bbox = None
			bbox0 = None
			layer = False

			# parsing the XML document to the root (setup) of the document
			tree = ET.parse(self.get_capabilities)
			root = tree.getroot()
			#pdb.set_trace()

			#WFS ver. 2.x.x
			for elem in root.findall('./{http://www.opengis.net/wfs/2.0}FeatureTypeList/{http://www.opengis.net/wfs/2.0}FeatureType'):
				for child in elem:
					if child.text:
						if ":" in child.text:
							layer_string = child.text.split(":")[1]
					if child.tag == '{http://www.opengis.net/wfs/2.0}Name' and (child.text in self.layer_name or layer_string in self.layer_name):
						layer = True

					if layer and (child.tag == '{http://www.opengis.net/ows/1.1}WGS84BoundingBox'):

						for elem in child.getchildren():
							if "LowerCorner" in elem.tag:
								lonlat1 = elem.text.split()
								lonlat1 = [float(i) for i in lonlat1]
							elif "UpperCorner" in elem.tag:
								lonlat2 = elem.text.split() 
								lonlat2 = [float(i) for i in lonlat2]	
							else:
								raise Exception("Unexpected bbox value when parsing xml: {}. Expected LowerCorner or UpperCorner".format(element.tag))	
						
						bbox0 = lonlat1 + lonlat2
						layer = False
						break


			#WFS ver. 1.x.x (1.0.x, 1.1.x)
			for elem in root.findall('./{http://www.opengis.net/wfs}FeatureTypeList/{http://www.opengis.net/wfs}FeatureType'):
				for child in elem:
					if child.text:
						if ':' in child.text:
							layer_string = child.text.split(':')[1]
					if child.tag == '{http://www.opengis.net/wfs}Name'  and (child.text in self.layer_name or layer_string in self.layer_name):
						layer = True

					if layer and (child.tag == '{http://www.opengis.net/ows}WGS84BoundingBox' or child.tag == '{http://www.opengis.net/wfs}LatLongBoundingBox'):

						if child.tag == '{http://www.opengis.net/wfs}LatLongBoundingBox':
							bbox=[child.attrib['minx'], child.attrib['miny'], child.attrib['maxx'], child.attrib['maxy']]
							for i in range(len(bbox)):
								bbox[i]=float(bbox[i])
						else:
							for elem in child.getchildren():
								if "LowerCorner" in elem.tag:
									lonlat1 = elem.text.split()
									lonlat1 = [float(i) for i in lonlat1]
								elif "UpperCorner" in elem.tag:
									lonlat2 = elem.text.split() 
									lonlat2 = [float(i) for i in lonlat2]	
								else:
									raise Exception("Unexpected bbox value when parsing xml: {}. Expected LowerCorner or UpperCorner".format(element.tag))	
							bbox0 = lonlat1 + lonlat2
						layer = False


			# conversion of bbox0 (WGS84 to self.crs)
			if bbox == None:


				#fixing problem with EPSG: 4269 (switch lat and long)
				#if epsg_code == 4269:
				#	bbox0=[bbox0[1],bbox0[0],bbox0[3],bbox0[2]]
				#	print('EPSG 4269, coordinates have been swichted for correct transformation')

				inProj = Proj(init='epsg:4326')
				outProj = Proj(epsg_code)
				x1,y1 = transform(inProj,outProj,bbox0[0],bbox0[1])
				x2,y2 = transform(inProj,outProj,bbox0[2],bbox0[3])
				bbox=[x1,y1,x2,y2]

			# throw exception if the bbox is not found
			if not bbox:
				raise Exception("Bounding box information not found for the layer.")

			return bbox

	def create_empty_raster(self, output_name, resolution=1000, driver='GTiff'):
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

		pdb.set_trace()
		crs_in_degrees = ['4269','4326']

		if any(x in self.crs for x in crs_in_degrees):
			#if crs_in_degrees[0] in self.crs:

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

		
		minx = floor(bbox[0]/resolution) * resolution
		miny = floor(bbox[1]/resolution) * resolution
		maxx = ceil(bbox[2]/resolution) * resolution
		maxy = ceil(bbox[3]/resolution) * resolution

		# Calculate the scale
		# Note, the meaning of x and y changes between crs! Now, width = x, height = y. Make this more robust at some point.
		width = int((maxx - minx) / resolution)
		height = int((maxy - miny) / resolution)

		#if [width, height] == [1,1]:



		# This ties spatial coordinates and image coordinates together.
		transform = rasterio.transform.from_origin(minx, maxy, resolution, resolution)

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
			crs=crs,
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
	validate(process.url, process.layer_name, process.crs, process.layer_bbox, process.bin_raster_path, "../../validation21764.tif")
