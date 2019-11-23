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


from Projection import is_first_axis_east


def create_empty_raster(output_path, crs, bbox, resolution, driver='GTiff'):
	''' This function creates an empty raster file with the provided parametres.
	args:
		output_name: the path where the dataset will be created
		driver: GDAL raster driver to create datasets
	returns: the path where the dataset was created (the same as output_name)
	'''


	#TODO: replace output_name and output_dir with output_path


	# Round up or down to regarding to the resolution value.
	
	# Some helper functions
	def round_down(val):
		return floor(val / resolution) * resolution
	def round_up(val):
		return ceil(val / resolution) * resolution

	minx = round_down(bbox[0])
	miny = round_down(bbox[1])
	maxx = round_up(bbox[2])
	maxy = round_up(bbox[3])

	# Calculate the scale
	# "Normal" case
	if is_first_axis_east(crs):
		width = round((maxx - minx) / resolution)
		height = round((maxy - miny) / resolution)
		transform = rasterio.transform.from_origin(minx, maxy, resolution, resolution)
	# If north axis is given first.
	else:
		height = round((maxx - minx) / resolution)
		width = round((maxy - miny) / resolution)
		transform = rasterio.transform.from_origin(miny, maxx, resolution, resolution)

	# Init raster with zeros.
	data = np.zeros(shape=(height, width))

	# Create new dataset file
	dataset = rasterio.open(
		output_path,
		'w', # Write mode
		driver=driver,
		nodata = -99,
		height=height,
		width=width,
		count=1,
		dtype=str(data.dtype),
		crs=crs.crs_code,
		transform=transform,
	)

	# Write numpy matrix to the dataset.
	dataset.write(data, 1)
	dataset.close()

	return output_path
		

def convert_to_gpkg(crs, output_dir, resolution, input_file):
	# Create layer name based on the raster file name
	dst_layername = input_file.split('/')[-1].split('.')[0]
	
	with rasterio.open(input_file, driver= 'GTiff', mode='r') as src:
		image = src.read(1)
		
		# Create 1 pixel buffer around areas to smooth output.
		smoothed = scipy.ndimage.percentile_filter(image, 99, (30,30))

		# Mask value is 1, which means data
		mask = smoothed == 1

		# Tolerance for douglas peucker simplification
		tol = resolution
		
		# Transformation and convertion from shapely shape to geojson-like object for fiona.
		feats = []
		for (s,v) in shapes(smoothed, mask=mask, transform=src.transform):
			shp = shape(s).simplify(tol)
			if crs.output_transform:
				shp = shapely_transform(crs.output_transform, shp)
			feats.append(shp)

		results = ({'geometry': mapping(f), 'properties': {}} for f in feats)

	with fiona.open(
			output_dir + dst_layername + ".gpkg" , 'w', 
			driver="GPKG",
			crs=fiona.crs.from_string(crs.output_crs.to_proj4()) if crs.output_crs else src.crs,
			schema={'geometry': 'Polygon', 'properties': {}}) as dst:
		dst.writerecords(results)

