import rasterio
import numpy as np
from math import floor, ceil
import utm


class ResultData():
	
	def __init__(self, crs, extent, resolution, output_dir):
		self.crs = crs
		self.extent = extent
		self.resolution = resolution
		self.output_dir = output_dir

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
			_min = utm.from_latlon(self.extent[0], self.extent[1])
			#TODO: this needs to be converted into the same crs as _min
			_max = utm.from_latlon(self.extent[2], self.extent[3])
			bbox = [_min[0], _min[1], _max[0], _max[1]]

		else:
			bbox = self.extent

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
		