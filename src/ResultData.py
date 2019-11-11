import rasterio
import numpy as np
from math import floor, ceil

import logging
# logging levels = DEBUG, INFO, WARNING, ERROR, CRITICAL
import datetime
logging.basicConfig(filename=datetime.datetime.now().strftime("%d.%b_%Y_%H:%M:%S")' + .log', level=logging.INFO)

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

		return self.output_dir + output_name
		