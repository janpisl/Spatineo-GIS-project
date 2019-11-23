import configparser
import argparse

import rasterio
import rasterio.mask
import json
from geojson import Feature
from shapely.geometry import shape, MultiPolygon, asShape
from shapely.ops import cascaded_union
import ogr

import pdb
import numpy as np
from scipy import stats

import logging
# logging levels = DEBUG, INFO, WARNING, ERROR, CRITICAL
import datetime
logging.basicConfig(filename=datetime.datetime.now().strftime("%d.%b_%Y_%H_%M_%S") + '.log', level=logging.INFO)



def solve(features, empty_raster, output_path, bin_output_path):
	open_raster = rasterio.open(empty_raster)
	eval_raster = open_raster.read()
	norm_raster = np.copy(eval_raster)
	request_counter = 0
	nd = open_raster.nodata
	logging.info("Iterating through geojson objects...")
	for feat in features['features']:
		request_counter += 1
		if request_counter % 1000 == 0:
			logging.debug("Feature no. {}".format(request_counter))
		
		mask, t, w = rasterio.mask.raster_geometry_mask(open_raster, [feat['geometry']], crop=False, invert=True)

		props = feat['properties']
		if props['imageAnalysisResult'] == 1:
			norm_raster[0][mask] += 1
		elif (props['imageAnalysisResult'] == 0 or props['imageAnalysisResult'] == -1):
			norm_raster[0][mask] += 1
			eval_raster[0][mask] += 1
		else:
			logging.warning("unexpected imageTestResult value: {}".format(props['imageAnalysisResult']))
			logging.warning(feat)


	eval_raster = np.divide(eval_raster, norm_raster, out=np.zeros_like(eval_raster), where=norm_raster != 0)
	zero_mask = norm_raster[0] == 0
	logging.info("there was {} requests".format(request_counter))
	# Save the image into disk.     
	img_output = rasterio.open(
		output_path,
		'w',
		driver='GTiff',
		nodata=nd,
		height=open_raster.height,
		width = open_raster.width,
		count=1,
		dtype = open_raster.dtypes[0],
		crs=open_raster.crs,
		transform=open_raster.transform)   
	img_output.write(eval_raster)
	img_output.close()
	logging.debug("norm average: ",np.average(norm_raster))

	magic_constant = 0.1
	threshold = np.average(eval_raster)*magic_constant
	logging.debug("threshold is: {}".format(threshold))
	binary_raster = eval_raster < threshold
	binary_raster[0][zero_mask] = False

	# Save the image into disk.        
	bin_output = rasterio.open(
		bin_output_path,
		'w',
		nbits = 1,
		driver='GTiff',
		nodata=99,
		height=open_raster.height,
		width = open_raster.width,
		count=1,
		dtype = 'uint8',
		crs=open_raster.crs,
		transform=open_raster.transform)   
	bin_output.write(binary_raster.astype(np.uint8))
	bin_output.close()

	logging.info("algorithm finished, binary raster has been created")

	

if __name__ == '__main__':
	# This is an example how we can run the algorithm separately (without Process.py) if we need to.
	parser = argparse.ArgumentParser()
	parser.add_argument("path_to_config", help="Path to the file containing configuration.")
	args = parser.parse_args()

	config = configparser.ConfigParser()
	data = config.read(args.path_to_config)
	if len(data) == 0:
		raise Exception("Configuration file not found.")

	# temporary file - stays hard-coded 	
	empty_raster = "../../tmp.tif"
	responses_path = config.get('data','response_file')
	with open(responses_path) as source:
		requests = json.load(source)

	#alg = Algorithm(empty_raster,requests, "WMS")
	alg = Algorithm(empty_raster,requests, "WFS")
	raster = alg.solve(config.get('data','raster_output_path'), config.get('data','binary_raster_output_path'))