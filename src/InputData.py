import json
from geojson import Polygon, Feature, FeatureCollection

from Projection import Projection

class InputData():
	
	def __init__(self, file_path):
		with open(file_path) as source:
			requests = json.load(source)
		self.layer_key = requests['layerKey']
		self.responses = requests['results']
		self.crs = Projection(self.layer_key['crs'])

	def get_crs_name(self):
		return self.layer_key['crs']

	def get_layer_name(self):
		return self.layer_key['layerName']
		
	def get_request_url(self):
		return self.responses[0]['url'].split("?")[0]

	def get_bboxes_as_geojson(self):
		''' This method converts response file to geojson geometries. imageAnalysisResult is included to the geojson features.
		returns: list of geojson elements
		'''
		features = []
		count = 0
		print("Creating geojson objects.")
		for res in self.responses:
			count += 1
			if count % 1000 == 0:
				print("Res. no {}".format(count))
			if ('imageAnalysisResult' not in res.keys() or 'testResult' not in res.keys()
				or res['testResult'] in ['2', '3', '4', '5']):
				continue
			# Convert bbox as a list.
			bbox = list(map(float, res['bBox'].split(',')))
			# Create a closed Polygon following the edges of the bbox.
			if self.crs.is_first_axis_east():
				g = Polygon([[(bbox[0], bbox[1]), (bbox[0], bbox[3]), (bbox[2], bbox[3]), (bbox[2], bbox[1]), (bbox[0], bbox[1])]])
			else:
				g = Polygon([[(bbox[1], bbox[0]), (bbox[3], bbox[0]), (bbox[3], bbox[2]), (bbox[1], bbox[2]), (bbox[1], bbox[0])]])
			# Save other data
			props = {
				'imageAnalysisResult': res['imageAnalysisResult'],
				'testResult': res['testResult'],
				'requestTime': res['requestTime']
			}
			feat = Feature(geometry = g, properties = props)
			
			features.append(feat)

		feat_c = FeatureCollection(features)
		
		with open('../data.geojson', 'w') as outfile:
			json.dump(feat_c, outfile)
		return feat_c