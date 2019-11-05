import rasterio
import rasterio.mask
import json
from geojson import Polygon
import pdb
from shapely.geometry import shape, mapping
import numpy as np
from scipy import stats

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
		print("raster average: ",np.average(raster))
		
		return np.average(raster)

	def solve(self, output_path, bin_output_path):
		eval_raster = self.raster.read()
		norm_raster = np.copy(eval_raster)
		request_counter = 0
		print("Iterating through geojson objects...")
		for feat in self.features:
			request_counter += 1
			if request_counter % 1000 == 0:
				print("Feature no. {}".format(request_counter))
			# this is a really dirty solution
			#TODO: replace with a better one
			feat_format = str(feat).replace('[[', '[[[').replace(']]', ']]]')
			g = shape(json.loads(feat_format))
			ref_image, ref_transform = rasterio.mask.mask(self.raster, [mapping(g)], crop=False)
			nd = self.raster.nodata
			mask = ref_image[0] != nd

			# NOTE: The algorithm is changed to calculate negative results. The result is not yet adapted to use this.
			if feat['imageAnalysisResult'] == 1:
				# eval_raster[0][mask] += 1
				norm_raster[0][mask] += 1
			elif (feat['imageAnalysisResult'] == 0 or feat['imageAnalysisResult'] == -1):
				norm_raster[0][mask] += 1
				eval_raster[0][mask] += 1
			else:
				#TODO: exclude responses with feat['imageTestResult'] == None
				#this should be done earlier than here (no reason to iterate through them)
				print("unexpected imageTestResult value: {}".format(feat['imageAnalysisResult']))
				print(feat)
			
			#if i == 1000:
			#    ref_image_out = ref_image
			#i = i + 1
		eval_raster = np.divide(eval_raster, norm_raster, out=np.zeros_like(eval_raster), where=norm_raster != 0)
		print("there was {} requests".format(request_counter))
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
		print("norm average: ",np.average(norm_raster))

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
		img_output.close()

		test = rasterio.open(output_path)
		test_raster = test.read()
		
		#TODO: replace this with something sensible
		threshold = self.compute_threshold(eval_raster)
		print("threshold is: {}".format(threshold))
		binary_raster = eval_raster > threshold
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




if __name__ == '__main__':

	# This is an example how we can run the algorithm separately (without Process.py) if we need to.
	empty_raster = "../../tmp.tif"
	responses_path = "/home/jan/Documents/Aalto/Spatineo_Project/spatineo-aalto/converted_example_service.txt"
	with open(responses_path) as source:
		requests = json.load(source)

	#alg = Algorithm(empty_raster,requests, "WMS")
	alg = Algorithm(empty_raster,requests, "WFS")
	raster = alg.solve("../../ousdftput_tmp.tif")