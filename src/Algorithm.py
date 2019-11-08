import rasterio
import rasterio.mask
import json
from geojson import Feature
from shapely.geometry import shape, MultiPolygon, asShape
from shapely.ops import cascaded_union
import pdb
import numpy as np
from scipy import stats

import logging
# logging levels = DEBUG, INFO, WARNING, ERROR, CRITICAL
logging.basicConfig(level=logging.INFO)

#pdb.set_trace()

class Algorithm():
	def __init__(self, raster, input_data, service):
		'''
		args:
			raster = empty raster
			input_data = inputdata -object that contains all responses
			service = WMS/WFS
		'''	
		self.raster = rasterio.open(raster)
		self.service = service
		self.features = input_data.get_bboxes_as_geojson()
		

	def compute_threshold(self, raster):
		'''mode = stats.mode(raster, axis=None)[0][0]
		std = np.std(raster)
		mask = raster > (2*std +mode)
		avg = np.average(raster[0][mask])'''
		mode = stats.mode(raster, axis=None)[0][0]
		logging.debug("raster average: ",np.average(raster))
		
		return np.average(raster)

	def solve(self, output_path, bin_output_path):
		eval_raster = self.raster.read()
		norm_raster = np.copy(eval_raster)
		request_counter = 0
		logging.info("Iterating through geojson objects...")
		for feat in self.features['features']:
			request_counter += 1
			if request_counter % 1000 == 0:
				logging.debug("Feature no. {}".format(request_counter))
			ref_image, ref_transform = rasterio.mask.mask(self.raster, [feat['geometry']], crop=False)
			nd = self.raster.nodata
			mask = ref_image[0] != nd

			# NOTE: The algorithm is changed to calculate negative results. The result is not yet adapted to use this.
			props = feat['properties']
			if props['imageAnalysisResult'] == 1:
				# eval_raster[0][mask] += 1
				norm_raster[0][mask] += 1
			elif (props['imageAnalysisResult'] == 0 or props['imageAnalysisResult'] == -1):
				norm_raster[0][mask] += 1
				eval_raster[0][mask] += 1
			else:
				#TODO: exclude responses with feat['imageTestResult'] == None
				#this should be done earlier than here (no reason to iterate through them)
				logging.warning("unexpected imageTestResult value: {}".format(props['imageAnalysisResult']))
				logging.warning(feat)
			
			#if i == 1000:
			#    ref_image_out = ref_image
			#i = i + 1
		eval_raster = np.divide(eval_raster, norm_raster, out=np.zeros_like(eval_raster), where=norm_raster != 0)
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
			transform=self.raster.transform,)   
		img_output.write(eval_raster)
		img_output.close()
		logging.debug("norm average: ",np.average(norm_raster))

		'''
		img_output = rasterio.open(
			"../../output_data/norm_raster24274.tif",
			'w',
			driver='GTiff',
			nodata=nd,
			height=self.raster.height,
			width = self.raster.width,
			count=1,
			dtype = self.raster.dtypes[0],
			crs=self.raster.crs,
			transform=self.raster.transform,)   
		img_output.write(norm_raster)
		img_output.close()'''
		
		#TODO: replace this with something sensible
		threshold = self.compute_threshold(eval_raster)
		logging.debug("threshold is: {}".format(threshold))
		binary_raster = eval_raster < threshold
		#pdb.set_trace()
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
			transform=self.raster.transform,)   
		bin_output.write(binary_raster.astype(np.uint8))
		bin_output.close()


	def solve_simple(self, output_path, bin_output_path):
		
		pos_shape = None
		# shapely.geometry.asShape(self.features['features'][0]['geometry'])
		neg_shape = None
		
		request_counter = 0
		logging.info("Iterating through geojson objects...")
		for feat in self.features['features']:
			request_counter += 1
			if request_counter % 1000 == 0:
				logging.debug("Feature no. {}".format(request_counter))
			shp = shape(feat['geometry'])
			res = feat['properties']['imageAnalysisResult']
			if res == 1:
				if not pos_shape:
					pos_shape = asShape(shp)
				else:
					pos_shape.union(shp)
			elif res == 0:
				if not neg_shape:
					neg_shape = asShape(shp)
				neg_shape.union(shp)

		# what does merged mean?
		logging.info('merged!')
		result = pos_shape.difference(neg_shape)

		neg_feat = Feature(geometry=neg_shape, properties={})
		
		with open('../result_neg.geojson', 'w') as outfile:
			json.dump(neg_feat, outfile)

		pos_feat = Feature(geometry=pos_shape, properties={})
		
		with open('../result_pos.geojson', 'w') as outfile:
			json.dump(pos_feat, outfile)

		res_feat = Feature(geometry=result, properties={})
		
		with open('../result_union.geojson', 'w') as outfile:
			json.dump(res_feat, outfile)


if __name__ == '__main__':

	# This is an example how we can run the algorithm separately (without Process.py) if we need to.
	empty_raster = "../../tmp.tif"
	responses_path = "/home/jan/Documents/Aalto/Spatineo_Project/spatineo-aalto/converted_example_service.txt"
	with open(responses_path) as source:
		requests = json.load(source)

	#alg = Algorithm(empty_raster,requests, "WMS")
	alg = Algorithm(empty_raster,requests, "WFS")
	raster = alg.solve("../../ousdftput_tmp.tif")