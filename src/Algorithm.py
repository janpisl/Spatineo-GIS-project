import rasterio
import rasterio.mask
import json
from geojson import Polygon
import pdb
from shapely.geometry import shape, mapping
import numpy as np

#pdb.set_trace()

class Algorithm():
	def __init__(self, raster, responses, service):
		'''
		args:
			raster = empty raster
			data_file = a list of responses ('results' in the data file) for one layer key
			service = WMS/WFS
		'''	
		self.raster = rasterio.open(raster)
		self.responses = responses
		self.service = service
		self.features = self.parse_responses_to_geojson(self.responses)
		
	def parse_responses_to_geojson(self, responses):
		''' This method converts response file to geojson geometries. imageAnalysisResult is included to the geojson features.
		args:
			responses: parsed response file
		returns: list of geojson elements
		'''
		features = []
		for res in responses['results']:
			# Convert bbox as a list.
			bbox = list(map(float, res['bBox'].split(',')))
			# Create a closed Polygon following the edges of the bbox.
			feat = Polygon([(bbox[0], bbox[1]), (bbox[0], bbox[3]), (bbox[2], bbox[3]), (bbox[2], bbox[1]), (bbox[0], bbox[1])])
			# Store imageTestResult to the feature.
			feat['imageTestResult'] = res['imageAnalysisResult']
			features.append(feat)
		return features


	def solve(self, output_path):
		band1 = self.raster.read()
		band_out = np.copy(band1)
		for feat in self.features:
			# this is a really dirty solution
			#TODO: replace with a better one
			feat_format = str(feat).replace('[[', '[[[').replace(']]', ']]]')
			g = shape(json.loads(feat_format))
			ref_image, ref_transform = rasterio.mask.mask(self.raster, [mapping(g)], crop=False)
			nd = self.raster.nodata
			mask = ref_image[0] != nd
			if feat['imageTestResult'] == 1:
				band_out[0][mask] +=1
			elif feat['imageTestResult'] == -1:
				band_out[0][mask] -=1
			else:
				#TODO: exclude responses with feat['imageTestResult'] == None
				#this should be done earlier than here (no reason to iterate through them)
				print("unexpected imageTestResult value: {}".format(feat['imageTestResult']))
				#print(feat)

			#if i == 1000:
			#    ref_image_out = ref_image
			#i = i + 1
		#pdb.set_trace()

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
		img_output.write(band_out)
		img_output.close()





if __name__ == '__main__':

	# This is an example how we can run the algorithm separately (without Process.py) if we need to.
	empty_raster = rasterio.open("../../tmp.tif")
	responses_path = "/home/jan/Documents/Aalto/Spatineo_Project/spatineo-aalto/converted_example_service.txt"
	with open(responses_path) as source:
		requests = json.load(source)

	alg = Algorithm(empty_raster,requests, "WMS")
	raster = alg.solve("../../output_tmp.tif")