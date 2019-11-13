import json
from geojson import Polygon, Feature, FeatureCollection

import logging
# logging levels = DEBUG, INFO, WARNING, ERROR, CRITICAL
import datetime
logging.basicConfig(filename=datetime.datetime.now().strftime("%d.%b_%Y_%H_%M_%S") + '.log', level=logging.INFO)

from Projection import Projection, change_bbox_axis_order
from Capabilities import Capabilities

class InputData():
	
	def __init__(self, response_file_path, capabilities_path):

		with open(response_file_path) as source:
			requests = json.load(source)
		self.layer_key = requests['layerKey']
		self.responses = requests['results']
		self.crs = Projection(self.layer_key['crs'])
		self.capabilities = Capabilities(capabilities_path)

	def get_crs_name(self):
		return self.layer_key['crs']

	def get_layer_name(self):
		return self.layer_key['layerName']
		
	def get_request_url(self):
		return self.responses[0]['url'].split("?")[0]

	def get_capabilities_bbox(self):
		return self.capabilities.get_layer_bbox(self.get_layer_name(), self.crs)

	def get_service_type(self):
		return self.capabilities._get_service()

	def get_bboxes_as_geojson(self):
		''' This method converts response file to geojson geometries. imageAnalysisResult is included to the geojson features.
		returns: list of geojson elements
		'''
		features = []
		extent = self.get_capabilities_bbox()

		invalid_request_count = 0
		bbox_out_count = 0

		count = 0
		logging.info("Creating geojson objects.")
		for res in self.responses:
			count += 1
			if count % 1000 == 0:
				logging.debug("Result no. {}".format(count))

			# Filter out invalid test results
			if ('imageAnalysisResult' not in res.keys() or 'testResult' not in res.keys()
				or res['testResult'] != 0):
				invalid_request_count += 1
				continue

			# Convert bbox as a list.
			bbox = list(map(float, res['bBox'].split(',')))

			if not self.crs.is_first_axis_east():
				bbox = change_bbox_axis_order(bbox)
			
			# Tolerance helps to handle rounding problems in the border areas.
			unit = self.crs.get_coordinate_unit().lower()
			tolerance = 1 if unit == 'metre' else 0.000001

			inside = [
				bbox[0] >= extent[0] - tolerance,
				bbox[1] >= extent[1] - tolerance,
				bbox[2] <= extent[2] + tolerance,
				bbox[3] <= extent[3] + tolerance,
			]

			# Filter out requests out of the interest area
			if not all(inside):
				bbox_out_count += 1
				continue

			# Create a closed Polygon following the edges of the bbox.
			g = Polygon([[(bbox[0], bbox[1]), (bbox[0], bbox[3]), (bbox[2], bbox[3]), (bbox[2], bbox[1]), (bbox[0], bbox[1])]])
			
			# Save other data
			props = {
				'imageAnalysisResult': res['imageAnalysisResult'],
				'testResult': res['testResult'],
				'requestTime': res['requestTime']
			}
			feat = Feature(geometry = g, properties = props)
			
			features.append(feat)

		if invalid_request_count > 0:
			logging.info("Filtered {} requests away due to failed request.".format(invalid_request_count))

		if bbox_out_count > 0:
			logging.info("Filtered {} requests way because request bbox was not completely within layer bbox".format(bbox_out_count))

		feat_c = FeatureCollection(features)
		
		#with open('../data.geojson', 'w') as outfile:
		#	json.dump(feat_c, outfile)
		return feat_c