import rasterio
from rasterio.features import shapes
from shapely.geometry import shape, mapping
from shapely.ops import transform as shapely_transform # TODO: check naming if it overlapping or not to variables of this file?
import fiona
import fiona.crs
import numpy as np
import scipy.ndimage
from math import floor, ceil
# from osgeo import gdal, ogr
# import sys

import logging
# logging levels = DEBUG, INFO, WARNING, ERROR, CRITICAL
import datetime
logging.basicConfig(filename="../../output_data/logs/" + datetime.datetime.now().strftime("%d.%b_%Y_%H_%M_%S") + '.log', level=logging.INFO)

class ResultData():
	
	def __init__(self, crs, extent, output_dir):
		self.crs = crs
		self.extent = extent

		unit = crs.get_coordinate_unit().lower()
		if unit == 'metre':
			self.resolution = 1000
		elif unit == 'degree':
			self.resolution = 0.01
		else:
			raise Exception("The used coordinate unit ({}) is not configured. Cannot continue.".format(unit))

		self.output_dir = output_dir

	def create_empty_raster(self, output_name, driver='GTiff'):
		''' This function creates an empty raster file with the provided parametres.
		args:
			output_name: the path where the dataset will be created
			driver: GDAL raster driver to create datasets
		returns: the path where the dataset was created (the same as output_name)
		'''

		bbox = self.extent

		# Round up or down to regarding to the resolution value.
		
		# Some helper functions
		def round_down(val):
			return floor(val / self.resolution) * self.resolution
		def round_up(val):
			return ceil(val / self.resolution) * self.resolution

		minx = round_down(bbox[0])
		miny = round_down(bbox[1])
		maxx = round_up(bbox[2])
		maxy = round_up(bbox[3])

		# Calculate the scale
		# "Normal" case
		if self.crs.is_first_axis_east():
			width = round((maxx - minx) / self.resolution)
			height = round((maxy - miny) / self.resolution)
			transform = rasterio.transform.from_origin(minx, maxy, self.resolution, self.resolution)
		# If north axis is given first.
		else:
			height = round((maxx - minx) / self.resolution)
			width = round((maxy - miny) / self.resolution)
			transform = rasterio.transform.from_origin(miny, maxx, self.resolution, self.resolution)

		# Init raster with zeros.
		data = np.zeros(shape=(height, width))

		# Create new dataset file
		dataset = rasterio.open(
			self.output_dir + output_name,
			'w', # Write mode
			driver=driver,
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

		return self.output_dir + output_name
		

	def convert_to_gpkg(self, input_file):
		# Create layer name based on the raster file name
		dst_layername = input_file.split('/')[-1].split('.')[0]
		
		with rasterio.open(input_file, driver= 'GTiff', mode='r') as src:
			image = src.read(1)
			
			# Create 1 pixel buffer around areas to smooth output.
			buffered = scipy.ndimage.maximum_filter(image, (3,3))

			# Mask value is 1, which means data
			mask = buffered == 1

			# # Tolerance for douglas peucker simplification
			# tol = self.resolution
			
			# Transformation and convertion from shapely shape to geojson-like object for fiona.
			feats = []
			for (s,v) in shapes(buffered, mask=mask, transform=src.transform):
				shp = shape(s)
				if self.crs.output_transform:
					shp = shapely_transform(self.crs.output_transform, shp)
				feats.append(shp)

			results = ({'geometry': mapping(f), 'properties': {}} for f in feats)

		with fiona.open(
				self.output_dir + dst_layername + ".gpkg" , 'w', 
				driver="GPKG",
				crs=fiona.crs.from_epsg(self.crs.output_crs.to_epsg()) if self.crs.output_crs else src.crs,
				schema={'geometry': 'Polygon', 'properties': {}}) as dst:
			dst.writerecords(results)
	
