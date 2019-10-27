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

from Algorithm import Algorithm
#pdb.set_trace()

from pyproj import Proj, transform

class Process():

	def __init__(self, cfg):
		#self.response_file_path = 'converted_example_service.txt'
		self.response_file_path = cfg.get('data', 'response_file')
		self.get_capabilities = cfg.get('data', 'get_capabilities')
		self.requests = self.load_requests(self.response_file_path)
		self.service = self.load_service(self.get_capabilities)
		self.crs = self.requests[3]['layerKey']['crs'] 
		self.layer_name = self.requests[3]['layerKey']['layerName']
		print(self.layer_name)
		self.layer_bbox = self.get_layer_bbox(self.layer_name, self.crs, self.service)
		#print(self.layer_bbox)
		self.raster = self.create_empty_raster('../../tmp.tif', self.crs, self.layer_bbox)
		try: 
			self.output_raster_path = cfg.get('data', 'raster_output_path')
		except:
			self.output_raster_path = '../../out.tif'
		try:
			self.bin_raster_path = cfg.get('data', 'binary_raster_output_path')
		except:
			self.bin_raster_path = '../../bin_out.tif'

	def load_service(self, get_capabilities):
		tree = ET.parse(self.get_capabilities)
		root = tree.getroot()
		
		service_name = None
		for element in root.findall('{http://www.opengis.net/ows/1.1}ServiceIdentification/{http://www.opengis.net/ows/1.1}ServiceType'):
			service_name = element.text

		for element in root.findall('{http://www.opengis.net/wms}Service/{http://www.opengis.net/wms}Name'):
			service_name = element.text		
		
		return service_name


	def load_requests(self, path):
		with open(path) as source:
			requests = json.load(source)

		return requests


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
				if element.tag == '{http://www.opengis.net/wms}BoundingBox' and element.attrib['CRS'] == self.crs and layer:
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
			for element in root.findall('./{http://www.opengis.net/wfs/2.0}FeatureTypeList/{http://www.opengis.net/wfs/2.0}FeatureType'):
				for child in element:
					if child.text:
						if ":" in child.text:
							layer_string = child.text.split(":")[1]
					if child.tag == '{http://www.opengis.net/wfs/2.0}Name' and (child.text in self.layer_name or layer_string in self.layer_name):
						layer = True

					if layer and (child.tag == '{http://www.opengis.net/ows/1.1}WGS84BoundingBox'):

						for element in child.getchildren():
							if "LowerCorner" in element.tag:
								lonlat1 = element.text.split()
								lonlat1 = [float(i) for i in lonlat1]
							elif "UpperCorner" in element.tag:
								lonlat2 = element.text.split() 
								lonlat2 = [float(i) for i in lonlat2]	
							else:
								raise Exception("Unexpected bbox value when parsing xml: {}. Expected LowerCorner or UpperCorner".format(element.tag))	
						
						bbox0 = lonlat1 + lonlat2
						layer = False
						break


			#WFS ver. 1.x.x (1.0.x, 1.1.x)
			for element in root.findall('./{http://www.opengis.net/wfs}FeatureTypeList/{http://www.opengis.net/wfs}FeatureType'):
				for child in element:
					if child.tag == '{http://www.opengis.net/wfs}Name' and (child.text in self.layer_name):
						layer = True
				
					if layer and (child.tag == '{http://www.opengis.net/ows}WGS84BoundingBox'):
						for tag in root.iter('{http://www.opengis.net/ows}LowerCorner'):
							lonlat1 = tag.text.split()
							lonlat1 = [float(i) for i in lonlat1]

						for tag in root.iter('{http://www.opengis.net/ows}UpperCorner'):
							lonlat2 = tag.text.split() 
							lonlat2 = [float(i) for i in lonlat2]
						
						bbox0 = lonlat1 + lonlat2

					#ver 1.0.x
					if layer and (child.tag == '{http://www.opengis.net/wfs}LatLongBoundingBox'):
						bbox0=child.attrib
						bbox=[bbox0['minx'], bbox0['miny'], bbox0['maxx'], bbox0['maxy']]
						for i in range(len(bbox)):
							bbox[i]=float(bbox[i])

				# in case layer name needs to be exctracted from string (e.g. pnr:Paikka, layer name is Paikka)
				if layer == False:
					for child in element:
						if child.tag == '{http://www.opengis.net/wfs}Name':
							index=child.text.rfind(':')
							string=child.text[index+1:]
							if string in self.layer_name:
								layer = True

						if layer and (child.tag == '{http://www.opengis.net/ows}WGS84BoundingBox'):
							for tag in root.iter('{http://www.opengis.net/ows}LowerCorner'):
								lonlat1 = tag.text.split()
								lonlat1 = [float(i) for i in lonlat1]

							for tag in root.iter('{http://www.opengis.net/ows}UpperCorner'):
								lonlat2 = tag.text.split() 
								lonlat2 = [float(i) for i in lonlat2]
						
							bbox0 = lonlat1 + lonlat2

						#ver 1.0.x
						if layer and (child.tag == '{http://www.opengis.net/wfs}LatLongBoundingBox'):
							bbox0=child.attrib
							bbox=[bbox0['minx'], bbox0['miny'], bbox0['maxx'], bbox0['maxy']]
							for i in range(len(bbox)):
								bbox[i]=float(bbox[i])
					
						if index == -1:
							raise Exception("Layer name not found.")

				if layer == True:
					break
			#CONVERSION of bbox0 (4326 > self.crs)
			if bbox == None:
				#fixing problem with EPSG: 4269 (switch lat and long)
				if '4269' in self.crs:
					bbox0=[bbox0[1],bbox0[0],bbox0[3],bbox0[2]]
					print('EPSG 4269, coordinates have been swichted for correct transformation')

				inProj = Proj(init='epsg:4326')
				outProj = Proj(self.crs)
				x1,y1 = transform(inProj,outProj,bbox0[0],bbox0[1])
				x2,y2 = transform(inProj,outProj,bbox0[2],bbox0[3])
				bbox=[x1,y1,x2,y2]

			# throw exception if the bbox is not found
			if not bbox:
				raise Exception("Bounding box information not found for the layer.")

			return bbox

	def create_empty_raster(self, output_name, crs, bbox, resolution=1000, driver='GTiff'):
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
		minx = floor(bbox[0]/resolution) * resolution
		miny = floor(bbox[1]/resolution) * resolution
		maxx = ceil(bbox[2]/resolution) * resolution
		maxy = ceil(bbox[3]/resolution) * resolution

		# Calculate the scale
		# Note, the meaning of x and y changes between crs! Now, width = x, height = y. Make this more robust at some point.
		width = int((maxx - minx) / resolution)
		height = int((maxy - miny) / resolution)

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
	#print("Process successfully finished. Output raster has been written to a location specified in your ini file.")