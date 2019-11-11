from osgeo import ogr, osr, gdal
import rasterio.features
import geojson
import numpy as np
import pdb
import configparser
import argparse

import logging
# logging levels = DEBUG, INFO, WARNING, ERROR, CRITICAL
import datetime
logging.basicConfig(filename=datetime.datetime.now().strftime("%d.%b_%Y_%H:%M:%S")' + .log', level=logging.INFO)




'''
[validation]
wfs_url = https://geo.sv.rostock.de/geodienste/hospize/wfs
layer_name = hospize:hro.hospize.hospize
srs = urn:ogc:def:crs:EPSG::25833
bbox = 303000,5993000,325000,6015000
raster_to_validate = /Users/juhohanninen/spatineo/result_out44.tif
validation_file = /Users/juhohanninen/spatineo/validation.tif
'''

def validate(url, layer_name, srs, bbox, result_file, output_path):

	# Set the driver (optional)
	wfs_drv = ogr.GetDriverByName('WFS')

	# change bbox from a list into a string, remove spaces and brackets
	bbox_str = ''.join(char for char in str(bbox) if char not in '[] ')
	# get just the layer name (as opposed to a URL)
	layer_name = layer_name.split(":")[-1]

	# Speeds up querying WFS capabilities for services with alot of layers
	gdal.SetConfigOption('OGR_WFS_LOAD_MULTIPLE_LAYER_DEFN', 'NO')

	# Set config for paging. Works on WFS 2.0 services and WFS 1.0 and 1.1 with some other services.
	gdal.SetConfigOption('OGR_WFS_PAGING_ALLOWED', 'YES')
	gdal.SetConfigOption('OGR_WFS_PAGE_SIZE', '10000')

	# Fix for SSL connection errors
	gdal.SetConfigOption('GDAL_HTTP_UNSAFESSL', 'YES')

	# Open the webservice
	req_url = "{}?service=wfs&version=2.0.0&srsName={}&BBOX={}".format(url, srs, bbox_str)
	wfs_ds = wfs_drv.Open('WFS:' + req_url)
	if not wfs_ds:
		logging.error("Couldn't open connection to the server.")
		#raise Exception("Couldn't open connection to the server.")
		return -1

	shapes = []

	# Get a specific layer
	layer = wfs_ds.GetLayerByName(layer_name)
	if not layer:
		raise Exception("Couldn't find layer in service")

	logging.info("Layer: {}, Features: {}".format(layer.GetName(), layer.GetFeatureCount()))

	# iterate over features

	logging.info("Start iteration through features.")

	feat = layer.GetNextFeature()
	count = 0
	while feat is not None:
		count += 1
		if count % 100 == 0:
			logging.info("Feature: {}".format(count))
		geom = feat.GetGeometryRef()
		json_feat = geojson.loads(geom.ExportToJson())
		shapes.append(json_feat)

		feat = layer.GetNextFeature()

	feat = None

	# Close the connection
	wfs_ds = None
	logging.info("Iteration done. Creating validation.")
	# Open the file that we want to validate
	result = rasterio.open(result_file)
	if count == 0:
		logging.info("No features in the layer.")
		real_data = np.zeros_like(result.read(1))
	else:
		real_data = rasterio.features.rasterize(
			shapes,
			out_shape=result.shape,
			transform=result.transform,
			dtype='uint8'
		)

	# Since result is binary, the comparison is 0 if some value was the same.
	# 1 if we got false negative and -1 if we got false positive.
	comparison = result.read(1) - real_data
	output = rasterio.open(
		output_path,
		'w',
		driver='GTiff',
		nodata=5,
		height=result.height,
		width=result.width,
		count=1,
		dtype='uint8',
		crs=result.crs,
		transform=result.transform
	)

	output.write(comparison, 1)
	output.close()
	logging.info("Done")

	#TODO: write to file instead of stdout; iterate through all np.unique
	logging.info("Statistics:")
	if len(np.unique(comparison, return_counts = True)[1]) > 2:
		logging.warning("statistics are incomplete")

	logging.info("correct: {}%".format(round(100*np.unique(comparison, return_counts = True)[1][0]/np.size(comparison))))
	logging.info("incorrect: {}%".format(round(100*np.unique(comparison, return_counts = True)[1][1]/np.size(comparison))))

	return 0


if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument("path_to_config", help="Path to the file containing configuration.")
	args = parser.parse_args()

	config = configparser.ConfigParser()
	data = config.read(args.path_to_config)

	if len(data) == 0:
		raise Exception("Configuration file not found.")

	validate(
		config.get('validation', 'wfs_url'),
		config.get('validation', 'layer_name'),
		config.get('validation', 'srs'),
		config.get('validation', 'bbox'),
		config.get('validation', 'raster_to_validate'),
		config.get('validation', 'validation_file')
	)
