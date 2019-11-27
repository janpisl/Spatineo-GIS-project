import pyproj
import logging
# logging levels = DEBUG, INFO, WARNING, ERROR, CRITICAL
import datetime
logging.basicConfig(filename="../../output_data/logs/" + datetime.datetime.now().strftime("%d.%b_%Y_%H_%M_%S") + '.log', level=logging.INFO)

def solve_first_axis_direction(service_type, service_version, crs_name):
	version_num = [int(num) for num in service_version.split('.')]
	if service_type == 'WMS':
		if version_num[0] <= 1 and version_num[1] < 3:
			return 'east'
		return 'epsg'

	elif service_type == 'WFS':
		if version_num[0] == 1 and version_num[1] < 1:
			return 'east'
		if crs_name.startswith('http://www.opengis.net/gml/'):
			return 'east'
		if crs_name.startswith('urn:'):
			return 'epsg'
		return 'epsg'

	logging.warning("Couldn't solve first axis order. Using EPSG database info.")
	return 'epsg'

def is_first_axis_east(crs):
	# Check that the property exists. Otherwise use pyproj value.
	if hasattr(crs, 'first_axis_dir') and crs.first_axis_dir:
		return crs.first_axis_dir
	return crs.axis_info[0].direction.lower() == 'east'

def change_bbox_axis_order(bbox):
	""" Flip the axis order of the given bbox. """
	return [bbox[1], bbox[0], bbox[3], bbox[2]]


class CRS(pyproj.CRS):

	def __init__(self, crs_code, first_axis_dir):
		try:
			super().__init__(crs_code)
		except pyproj.exceptions.CRSError:
			assert crs_code == "CRS:84", "There is another crs code that pyproj.CRS cannot handle (apart from CRS:84): '{}'".format(crs_code)
			super().__init__("EPSG:4326")
			self.first_axis_dir = 'east'

		self.crs_code = crs_code
		if first_axis_dir in ('east', 'north'):
			self.first_axis_dir = first_axis_dir
		else:
			self.first_axis_dir = None
