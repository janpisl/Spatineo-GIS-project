import pdb
import rasterio
import configparser
import argparse
import json
import logging
import xml.etree.ElementTree as ET
import numpy as np

# logging levels = DEBUG, INFO, WARNING, ERROR, CRITICAL
import datetime
logging.basicConfig(filename="../../output_data/logs/" + datetime.datetime.now().strftime("%d.%b_%Y_%H_%M_%S") + '.log', level=logging.INFO)

from Algorithm import solve, compute_density_rasters
from Validate import validate
from InputData import get_resolution, get_service_type, get_bboxes_as_geojson
from ResultData import create_empty_raster, convert_to_gpkg
from Projection import CRS
from Capabilities import get_layer_bbox

class Process():

	def __init__(self, cfg):
		response_file_path = cfg.get('data', 'response_file')
		capabilities_path = cfg.get('data', 'get_capabilities')
		self.output_dir = cfg.get('data', 'output_dir')
		cfg_resolution = int(cfg.get('result', 'resolution'))
		try:
			output_crs = cfg.get('result', 'crs')
		except:
			output_crs = "EPSG:4326"
		self.output_crs = CRS(output_crs)
		file = response_file_path.split('/')[-1].split('.')[0]

		try:
			self.output_raster_path = cfg.get('data', 'raster_output_path')
			self.bin_raster_path = cfg.get('data', 'binary_raster_output_path')
			self.val_raster_output_path = cfg.get('data', 'validation_raster_output_path')
		except:
			self.output_raster_path = self.output_dir + file + ".tif"
			self.bin_raster_path = self.output_dir + "bin_" + file + ".tif"
			self.val_raster_output_path = self.output_dir + "val_" + file + ".tif"

		try:
			self.max_features_for_validation = int(cfg.get('other', 'max_features_for_validation'))
		except:
			self.max_features_for_validation = None

		with open(response_file_path) as source:
			self.responses_file = json.load(source)

		self.responses_header = self.responses_file['layerKey']
		self.responses = self.responses_file['results']

		self.layer_name = self.responses_header['layerName']
		raw_crs =  self.responses_header['crs']

		self.crs = CRS(raw_crs)
		self.resolution = get_resolution(self.crs, cfg_resolution)

		self.service_type = get_service_type(capabilities_path)
		try:
			self.service_version = self.responses[0]['url'].split("VERSION=")[1].split("&")[0]
		except:
			self.service_version = None

		#TODO: delete one of these two
		self.request_url = self.responses[0]['url'].split("?")[0]
		self.url = self.responses[0]['url'].split("?")[0]


		## INITIAL PROCESSING TO GET SMALLER BBOX
		#TODO: why is this returning tuple instead of a list??
		self.layer_bbox = get_layer_bbox(capabilities_path, self.layer_name, self.crs, self.service_type)

		#uses only 1/10 for bbox shrinking 
		self.features_sample = get_bboxes_as_geojson(self.layer_bbox, self.responses, self.crs, sample = True)

		self.coarse_raster = create_empty_raster(self.output_dir + "/" + "tmp_coarse.tif" , self.crs, self.layer_bbox, resolution="coarse")

		self.bbox = self.shrink_bbox(self.coarse_raster,self.features_sample)
		# If shrinked bbox is larger or equal to original, use original
		if (self.layer_bbox[3]-self.layer_bbox[1]) <= (self.bbox[3]-self.bbox[1]) and (self.layer_bbox[2]-self.layer_bbox[0]) <= (self.bbox[2]-self.bbox[0]):
			self.bbox = self.layer_bbox
			logging.info("Bounding box from get_capabilities is being used.")


		## END

		#until self.bbox is fixed, use layer_bbox as usual
		#self.features = get_bboxes_as_geojson(self.bbox, self.responses, self.crs)

		self.features = get_bboxes_as_geojson(self.bbox, self.responses, self.crs)
		self.raster = create_empty_raster(self.output_dir + "/" + "tmp.tif" , self.crs, self.bbox, self.resolution)



	def shrink_bbox(self,coarse_raster,features):

		eval_raster, norm_raster, request_counter = compute_density_rasters(features, coarse_raster)

		#do not compare against request_counter but np.sum(norm_raster) because that doesnt include invalid requests
		# or rathter np.max(norm_raster)
		bin_norm_raster = norm_raster > np.max(norm_raster)/1000

		open_coarse_raster = rasterio.open(coarse_raster)

		datapixel_indices = np.argwhere(bin_norm_raster == True)

		min_coords = open_coarse_raster.xy(np.max(datapixel_indices[:,1]), np.min(datapixel_indices[:,2]), offset='ll')
		max_coords = open_coarse_raster.xy(np.min(datapixel_indices[:,1]), np.max(datapixel_indices[:,2]), offset='ur')

		return [int(round(coord)) for coord in min_coords + max_coords]




	def run_algorithm(self):

		#a = Algorithm(self.raster, self.input_data, self.service_type, self.result)

		solve(self.features, self.raster, self.output_raster_path, self.bin_raster_path)
		convert_to_gpkg(self.crs, self.output_dir, self.resolution, self.bin_raster_path, self.output_crs)


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

	# validation of the result. 
	validate(process.url, process.layer_name, process.crs.crs_code, 
				process.layer_bbox, process.bin_raster_path, process.val_raster_output_path, 
				process.service_type, process.service_version, process.max_features_for_validation)
