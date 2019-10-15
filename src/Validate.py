from osgeo import ogr, osr, gdal
import rasterio.features
import geojson
import numpy as np

import configparser
import argparse

def validate(url, layer_name, srs, bbox, result_file, output_path):

	# Set the driver (optional)
	wfs_drv = ogr.GetDriverByName('WFS')

	# Speeds up querying WFS capabilities for services with alot of layers
	gdal.SetConfigOption('OGR_WFS_LOAD_MULTIPLE_LAYER_DEFN', 'NO')

	# Set config for paging. Works on WFS 2.0 services and WFS 1.0 and 1.1 with some other services.
	gdal.SetConfigOption('OGR_WFS_PAGING_ALLOWED', 'YES')
	gdal.SetConfigOption('OGR_WFS_PAGE_SIZE', '10000')

	# Open the webservice
	req_url = "{}?service=wfs&version=2.0.0&srsName={}&BBOX={}".format(url, srs, bbox)
	wfs_ds = wfs_drv.Open('WFS:' + req_url)
	if not wfs_ds:
		raise Exception("Couldn't open connection to the server.")


	shapes = []

	# Get a specific layer
	layer = wfs_ds.GetLayerByName(layer_name)
	if not layer:
		raise Exception("Couldn't find layer in service")

	print("Layer: {}, Features: {}".format(layer.GetName(), layer.GetFeatureCount()))

	# iterate over features

	print("Start iteration through features.")

	feat = layer.GetNextFeature()
	count = 1
	while feat is not None:
		if count % 100 == 0:
			print("Feature: {}".format(count))
		geom = feat.GetGeometryRef()
		json_feat = geojson.loads(geom.ExportToJson())
		shapes.append(json_feat)

		feat = layer.GetNextFeature()

	feat = None

	# Close the connection
	wfs_ds = None
	print("Iteration done. Creating validation.")
	# Open the file that we want to validate
	result = rasterio.open(result_file)

	real_data = rasterio.features.rasterize(
		shapes,
		out_shape=result.shape,
		transform=result.transform,
		dtype='int16'
	)

	# Since result is binary, the comparison is 0 if some value was the same.
	# 1 if we got false negative and -1 if we got false positive.
	comparison = result.read(1) - real_data

	output = rasterio.open(
		output_path,
		'w',
		driver='GTiff',
		nodata=-99,
		height=result.height,
		width=result.width,
		count=1,
		dtype='int16',
		crs=result.crs,
		transform=result.transform
	)

	output.write(comparison, 1)
	output.close()
	print("Done")

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
