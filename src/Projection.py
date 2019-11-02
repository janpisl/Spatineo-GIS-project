from pyproj import CRS

class Projection():
	def __init__(self, name, ne_axis_order=False):
		self.name = name
		self.crs = CRS(name)
		self.ne_axis_order = ne_axis_order

	def is_projected(self):
		return self.crs.is_projected

	def coordinate_unit(self):
		return self.crs.axis_info[0].unit_name

	def get_epsg(self):
		return self.crs.to_epsg()

def change_bbox_axis_order(bbox):
	""" Flip the axis order of the given bbox. """
	return [bbox[1], bbox[0], bbox[3], bbox[2]]


