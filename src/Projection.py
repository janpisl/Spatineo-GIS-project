from pyproj import CRS, Transformer
import pyproj
import logging
# logging levels = DEBUG, INFO, WARNING, ERROR, CRITICAL
import datetime
logging.basicConfig(filename="../../output_data/logs/" + datetime.datetime.now().strftime("%d.%b_%Y_%H_%M_%S") + '.log', level=logging.INFO)

class Projection():
	def __init__(self, name, output_crs_name=None, manual_first_axis_direction=None):
		self.name = name
		
		try:
			self.crs = CRS(name)
		except pyproj.exceptions.CRSError:
			if name == "CRS:84":
				self.crs = CRS("EPSG:4326")

		self.manual_first_axis_direction = manual_first_axis_direction
		self.from_wgs84_transformer = Transformer.from_crs("EPSG:4326", self.crs)

		if output_crs_name:
			self.output_crs = CRS(output_crs_name)
			self.output_transform = Transformer.from_crs(self.crs, self.output_crs).transform
		else:
			self.output_crs = None
			self.output_transform = None

	def is_projected(self):
		return self.crs.is_projected

	def get_coordinate_unit(self):
		return self.crs.axis_info[0].unit_name

	def get_epsg(self):
		return self.crs.to_epsg()

	def convert_from_wgs84(self, lon, lat):
		return self.from_wgs84_transformer.transform(lat, lon)

	def is_first_axis_east(self):
		dir = self.manual_first_axis_direction if self.manual_first_axis_direction else self.crs.axis_info[0].direction.lower()
		return dir.lower() == 'east'

def change_bbox_axis_order(bbox):
	""" Flip the axis order of the given bbox. """
	return [bbox[1], bbox[0], bbox[3], bbox[2]]


