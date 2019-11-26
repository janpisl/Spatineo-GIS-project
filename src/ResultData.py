from shapely.geometry import shape, mapping, MultiPolygon
from shapely.ops import transform as shapely_transform, cascaded_union # TODO: check naming if it overlapping or not to variables of this file?
import rasterio
from rasterio.features import shapes
import fiona
import fiona.crs
import numpy as np
import scipy.ndimage
from math import floor, ceil
# from osgeo import gdal, ogr
# import sys
from pyproj import Transformer
import logging
# logging levels = DEBUG, INFO, WARNING, ERROR, CRITICAL
import datetime
logging.basicConfig(filename="../../output_data/logs/" + datetime.datetime.now().strftime("%d.%b_%Y_%H_%M_%S") + '.log', level=logging.INFO)

from Projection import is_first_axis_east


def get_raster_shapes(resolution, bbox, crs):
	
	# Some helper functions
	def round_down(val):
		return floor(val / resolution) * resolution
	def round_up(val):
		return ceil(val / resolution) * resolution
	# Round up or down to regarding to the resolution value.
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


	return height, width, transform

def create_empty_raster(output_path, crs, bbox, resolution, max_raster_size, driver='GTiff'):
	''' This function creates an empty raster file with the provided parametres.
	args:
		output_name: the path where the dataset will be created
		driver: GDAL raster driver to create datasets
	returns: the path where the dataset was created (the same as output_name)
	'''


	skip_logging = False
	COARSE_RES = 50

	# if we pass resolution argument, choose such resolution that  height*width are approx. == COARSE_RES
	if resolution == "coarse":
		avg_dist = (abs(bbox[0] - bbox[2]) + abs(bbox[1] - bbox[3]))/2
		resolution = avg_dist/COARSE_RES
		skip_logging = True

	while True:
		height, width, transform = get_raster_shapes(resolution, bbox, crs)
		if height*width <= max_raster_size:
			break
		else:
			resolution = resolution*2

	if not skip_logging:
		logging.info("Resolution with which the analysis will be done set to: '{}' ".format(resolution))
		logging.info("Raster size set to {}, {}".format(height, width))
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
		

def convert_to_vector_format(crs, output_dir, resolution, input_file, output_crs):
	# Create layer name based on the raster file name
	dst_layername = input_file.split('/')[-1].split('.')[0]
	
	with rasterio.open(input_file, driver= 'GTiff', mode='r') as src:
		image = src.read(1)
		
		# Smooth output with median filter. TODO: Make take kernel size somehow from resolution
		smoothed = scipy.ndimage.median_filter(image, (10,10), mode='constant')

		# Mask value is 1, which means data
		mask = smoothed == 1

		# Tolerance for douglas peucker simplification
		tol = resolution
		
		if crs != output_crs:
			tr = Transformer.from_crs(crs, output_crs, always_xy=is_first_axis_east(output_crs)).transform
		else:
			tr = None

		# Transformation and convertion from shapely shape to geojson-like object for fiona.
		feats = []
		feats_original_crs = []
		for (s,v) in shapes(smoothed, mask=mask, transform=src.transform):
			shp = shape(s).simplify(tol)
			feats_original_crs.append(shp)
			if tr:
				shp = shapely_transform(tr, shp)
			feats.append(shp)


		feature = MultiPolygon(feats)
		result = {'geometry': mapping(feature), 'properties': {'resolution': resolution }} # TODO: The resolution is not the same than used!

	with fiona.open(
			output_dir + dst_layername + ".geojson" , 'w', 
			driver="GeoJSON",
			crs=fiona.crs.from_string(output_crs.to_proj4()) if output_crs else src.crs,
			schema={'geometry': feature.type, 'properties': {'resolution': 'int'}}) as dst:
		dst.write(result)

	return MultiPolygon(feats_original_crs).bounds
