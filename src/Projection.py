import pyproj
import logging
# logging levels = DEBUG, INFO, WARNING, ERROR, CRITICAL
import datetime
logging.basicConfig(filename="../../output_data/logs/" + datetime.datetime.now().strftime("%d.%b_%Y_%H_%M_%S") + '.log', level=logging.INFO)


def is_first_axis_east(crs):
	return crs.axis_info[0].direction.lower() == 'east'

def change_bbox_axis_order(bbox):
	""" Flip the axis order of the given bbox. """
	return [bbox[1], bbox[0], bbox[3], bbox[2]]


class CRS(pyproj.CRS):

	def __init__(self, crs_code):
		try:
			super().__init__(crs_code)
		except pyproj.exceptions.CRSError:
			assert crs_code == "CRS:84", "there is another crs code that pyproj.CRS cannot handle (apart from CRS:84): '{}'".format(crs_code)
			super().__init__("EPSG:4326")
			self.axis_info[0].direction = 'east'
			self.axis_info[1].direction = 'north'

		self.crs_code = crs_code

