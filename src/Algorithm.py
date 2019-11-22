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

class Algorithm():
	def __init__(self, raster, input_data, service, result):
		'''
		args:
			raster = empty raster
			input_data = inputdata -object that contains all responses
			service = WMS/WFS
		'''	
		self.raster = rasterio.open(raster)
		self.service = service
		self.features = input_data.get_bboxes_as_geojson()
		self.result = result
		

	def compute_threshold(self, raster):
		'''mode = stats.mode(raster, axis=None)[0][0]
		std = np.std(raster)
		mask = raster > (2*std +mode)
		avg = np.average(raster[0][mask])'''
		mode = stats.mode(raster, axis=None)[0][0]
		logging.debug("raster average: ",np.average(raster))
		
		return np.average(raster)*0.1

	def solve(self, output_path, bin_output_path):
		eval_raster = self.raster.read()
		norm_raster = np.copy(eval_raster)
		request_counter = 0
		nd = self.raster.nodata
		logging.info("Iterating through geojson objects...")
		for feat in self.features['features']:
			request_counter += 1
			if request_counter % 1000 == 0:
				logging.debug("Feature no. {}".format(request_counter))
			
			mask, t, w = rasterio.mask.raster_geometry_mask(self.raster, [feat['geometry']], crop=False, invert=True)

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
			height=self.raster.height,
			width = self.raster.width,
			count=1,
			dtype = self.raster.dtypes[0],
			crs=self.raster.crs,
			transform=self.raster.transform)   
		img_output.write(eval_raster)
		img_output.close()
		logging.debug("norm average: ",np.average(norm_raster))


		#TODO: replace this with something sensible
		threshold = self.compute_threshold(eval_raster)
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
			height=self.raster.height,
			width = self.raster.width,
			count=1,
			dtype = 'uint8',
			crs=self.raster.crs,
			transform=self.raster.transform)   
		bin_output.write(binary_raster.astype(np.uint8))
		bin_output.close()

		self.result.convert_to_gpkg(bin_output_path) # TODO: combine all result datasets to use this class


	def solve_simple(self, output_path, bin_output_path):
		
		pos_shape = []
		# shapely.geometry.asShape(self.features['features'][0]['geometry'])
		neg_shape = []
		pos_geom = ogr.Geometry(ogr.wkbMultiPolygon)
		neg_geom = ogr.Geometry(ogr.wkbMultiPolygon)
		request_counter = 0
		logging.info("Iterating through geojson objects...")
		for feat in self.features['features']:
			request_counter += 1
			if request_counter % 1000 == 0:
				
				pos_tmp = pos_geom.UnionCascaded()
				neg_tmp = neg_geom.UnionCascaded()

				try:
					pos_geom = ogr.Geometry(ogr.wkbMultiPolygon)
					neg_geom = ogr.Geometry(ogr.wkbMultiPolygon)
					pos_geom.AddGeometry(pos_tmp)
					neg_geom.AddGeometry(neg_tmp)
				except:
					logging.error('error')
				logging.debug("Feature no. {}".format(request_counter))
			
			geom = ogr.CreateGeometryFromJson(json.dumps(feat['geometry']))
			# shp = shape(feat['geometry'])
			res = feat['properties']['imageAnalysisResult']
			try:
				if res == 1:
					# if not pos_shape:
					# 	pos_shape = asShape(shp)
					# else:
					# 	pos_shape.union(shp)
					pos_geom.AddGeometry(geom)
				elif res == 0:
					# if not neg_shape:
					# 	neg_shape = asShape(shp)
					# else:
					# 	neg_shape.union(shp)
					# neg_shape.append(geom)
					neg_geom.AddGeometry(geom)
			except:
				logging.error('Error')


		logging.info('merged!')
		# pos_geom = ogr.Geometry(ogr.wkbMultiPolygon)
		# neg_geom = ogr.Geometry(ogr.wkbMultiPolygon)
		# pos = cascaded_union(pos_shape)
		# neg = cascaded_union(neg_shape)

		pos = pos_geom.UnionCascaded()
		neg = neg_geom.UnionCascaded()

		# result = pos.Difference(neg)
		# neg_feat = Feature(geometry=neg, properties={})
		
		with open('../result_neg.geojson', 'w') as outfile:
			outfile.write(neg.ExportToJson())
			# json.dump(neg_feat, outfile)

		# pos_feat = Feature(geometry=pos, properties={})
		
		with open('../result_pos.geojson', 'w') as outfile:
			outfile.write(pos.ExportToJson())

			# json.dump(pos_feat, outfile)

		# res_feat = Feature(geometry=result, properties={})
		
		# with open('../result_union.geojson', 'w') as outfile:
		# 	outfile.write(result.ExportToJson())
			# json.dump(res_feat, outfile)


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