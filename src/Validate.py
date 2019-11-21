from osgeo import ogr, osr, gdal
from owslib.wms import WebMapService
import rasterio.features
import geojson
import numpy as np
import pdb
import configparser
import argparse
import requests
from PIL import Image
import io
# from Capabilities import Capabilities

import logging
# logging levels = DEBUG, INFO, WARNING, ERROR, CRITICAL
import datetime
logging.basicConfig(filename="../../output_data/logs/" + datetime.datetime.now().strftime("%d.%b_%Y_%H_%M_%S") + '.log', level=logging.INFO)


'''
[validation]
wfs_url = https://geo.sv.rostock.de/geodienste/hospize/wfs
layer_name = hospize:hro.hospize.hospize
srs = urn:ogc:def:crs:EPSG::25833
bbox = 303000,5993000,325000,6015000
raster_to_validate = /Users/juhohanninen/spatineo/result_out44.tif
validation_file = /Users/juhohanninen/spatineo/validation.tif
'''
#"url": "http://paikkatieto.ymparisto.fi/arcgis/services/INSPIRE/SYKE_Hydrografia/MapServer/WmsServer?VERSION=1.3.0&SERVICE=WMS&REQUEST=GetMap&LAYERS=HY.Network.WatercourseLink&STYLES=&CRS=EPSG:3067&BBOX=353484.39290249243,6952336.504877807,515662.8104318712,7114514.922407186&WIDTH=256&HEIGHT=256&FORMAT=image/png&EXCEPTIONS=XML"


def test_pixel(image):

	for i in range(image.shape[0]):
		for j in range(image.shape[1]):
			try:
				if not np.array_equal(image[i][j], first_val):
					return True
			except UnboundLocalError:
				first_val = image[i][j]
	
	return False

def test_for_var(image):

	data_grid = np.empty([3,3])
	size = round(image.shape[0]/data_grid.shape[0])
	for m in range(3):
		for k in range(3):
			image_subset = image[m*size:(m+1)*size,k*size:(k+1)*size]

			#image_subset = image[m*size:(m+1)*size,k*size:(k+1)*size,:]
			data_grid[m][k] = test_pixel(image_subset)

	return data_grid



def validate_WMS(url, layer_name, srs, bbox, result_array, output_path, service_version):
	
	#TODO: CRS/SRS (depending on version)
	#TODO: set height & width to higher values so more features are rendered? what values does Spatineo use?? 
	if service_version is None:
		service_version = "1.3.0"

	req_url = "{}?VERSION={}&SERVICE=WMS&REQUEST=GetMap&LAYERS={}&STYLES=&CRS={}&BBOX={}&WIDTH=256&HEIGHT=256&FORMAT=image/png&EXCEPTIONS=XML".format(url, service_version, layer_name, srs, bbox)
	image = requests.get(req_url)
	logging.info("URL used for validation: {}".format(req_url))


	image = np.array(Image.open(io.BytesIO(image.content))) 

	real_data = test_for_var(image).astype("uint8")

	our_grid = test_for_var(result_array).astype("uint8")

	return real_data, our_grid

def validate_WFS(url, layer_name, srs, bbox, result_file, output_path, service_version,  max_features_for_validation):
	wfs_drv = ogr.GetDriverByName('WFS')

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

	#TODO: use version -> if service_version is not None: ...
	req_url = "{}?service=wfs&version=2.0.0&srsName={}&BBOX={}".format(url, srs, bbox)
	wfs_ds = wfs_drv.Open('WFS:' + req_url)
	if not wfs_ds:
		logging.error("Couldn't open connection to the server.")
		#raise Exception("Couldn't open connection to the server.")
		return None

	shapes = []

	# Get a specific layer
	layer = wfs_ds.GetLayerByName(layer_name)
	if not layer:
		raise Exception("Couldn't find layer in service")
   
	feature_count = layer.GetFeatureCount()
	if  max_features_for_validation is not None:
		if feature_count > int(max_features_for_validation):
			   logging.warning("Validation for layer {} skipped. there was too many features: {}".format(layer.GetName(), layer.GetFeatureCount()))
			   return None

	logging.info("Layer: {}, Features: {}".format(layer.GetName(), feature_count))

	# iterate over features

	logging.info("Start iteration through features.")

	feat = layer.GetNextFeature()
	count = 0

	while feat is not None:
		count += 1
		if feature_count > 5000:
			log_every = 1000				
		else:
			log_every = 100
		if count % log_every == 0:
			logging.info("Feature: {}".format(count))
		geom = feat.GetGeometryRef().GetLinearGeometry()
		json_feat = geojson.loads(geom.ExportToJson())
		shapes.append(json_feat)

		feat = layer.GetNextFeature()

	feat = None

	# Close the connection
	wfs_ds = None
	logging.info("Iteration done. Creating validation.")
	
	if count == 0:
		logging.info("No features in the layer.")
		real_data = np.zeros_like(result_file.read(1))
	else:
		real_data = rasterio.features.rasterize(
			shapes,
			out_shape=result_file.shape,
			transform=result_file.transform,
			dtype='uint8'
		)

	return real_data



def validate(url, layer_name, srs, bbox, result_path, output_path, service_type, service_version, max_features_for_validation):


	#self.service_type = Capabilities._get_service()
	logging.info("validation starts at {}".format(datetime.datetime.now()))
	# Open the file to be validated
	file = rasterio.open(result_path)

	# change bbox from a list into a string, remove spaces and brackets
	bbox_str = ''.join(char for char in str(bbox) if char not in '[] ')

	if service_type == 'WMS': 

		real_data, result = validate_WMS(url, layer_name, srs, bbox_str, file.read(1), output_path, service_version)
					
	elif service_type == 'WFS':

		real_data, result = validate_WFS(url, layer_name, srs, bbox_str, file, output_path, service_version, max_features_for_validation), file.read(1)
		
		if real_data is None:
			return -1

	# Since result is binary, the comparison is 0 if some value was the same.
	# 1 if we got false negative and -1 if we got false positive.
	comparison = result - real_data
	output = rasterio.open(
		output_path,
		'w',
		driver='GTiff',
		nodata=99,
		height=file.height,
		width=file.width,
		count=1,
		dtype='uint8',
		crs=file.crs,
		transform=file.transform
	)

	output.write(comparison, 1)
	output.close()
	logging.info("Statistics:")
	logging.info("This is the np.unique count: {}".format(np.unique(comparison, return_counts = True)[1]))

	for i in range(len(np.unique(comparison, return_counts = True)[0])):
		if np.unique(comparison, return_counts = True)[0][i] == 0:
			logging.info("Correct: {}%".format(round(100*np.unique(comparison, return_counts = True)[1][i]/np.size(comparison))))
		elif np.unique(comparison, return_counts = True)[0][i] == 1:
			logging.info("False positives: {}%".format(round(100*np.unique(comparison, return_counts = True)[1][i]/np.size(comparison))))
		# this is supposed to be -1 but since uint8 is 0 to 255 it underflows and makes it 255	
		elif np.unique(comparison, return_counts = True)[0][i] == 255:
			logging.info("False negatives: {}%".format(round(100*np.unique(comparison, return_counts = True)[1][i]/np.size(comparison))))		
		else:
			raise Exception("Unexpected values in the validation raster: {}".format(np.unique(comparison, return_counts = True)[0]))


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
		config.get('validation', 'validation_file'),
		config.get('validation', 'service_type')
	)






