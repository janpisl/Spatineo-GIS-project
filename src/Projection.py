from pyproj import CRS, Transformer

class Projection():
	def __init__(self, name, input_ne_axis_order=False):
		self.name = name
		self.crs = CRS(name)
		self.input_ne_axis_order = input_ne_axis_order
		self.from_wgs84_transformer = Transformer.from_crs("EPSG:4326", self.crs)
		self.to_web_mercator_transformer = Transformer.from_crs(self.crs, 3857)

	def is_projected(self):
		return self.crs.is_projected

	def coordinate_unit(self):
		return self.crs.axis_info[0].unit_name

	def get_epsg(self):
		return self.crs.to_epsg()

	def convert_from_wgs84(self, lon, lat):
		return self.from_wgs84_transformer.transform(lat, lon)

	def convert_to_web_mercator(self, x, y):
		return self.to_web_mercator_transformer.transform(x, y)

	def get_first_axis_direction(self):
		return self.crs.axis_info[0].direction

def change_bbox_axis_order(bbox):
	""" Flip the axis order of the given bbox. """
	return [bbox[1], bbox[0], bbox[3], bbox[2]]

