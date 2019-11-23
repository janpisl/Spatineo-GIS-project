from pyproj import Transformer
import pyproj
import logging
# logging levels = DEBUG, INFO, WARNING, ERROR, CRITICAL
import datetime
logging.basicConfig(filename="../../output_data/logs/" + datetime.datetime.now().strftime("%d.%b_%Y_%H_%M_%S") + '.log', level=logging.INFO)


'''
		if output_crs_name:
			self.output_crs = CRS(output_crs_name)
			self.output_transform = Transformer.from_crs(self.crs, self.output_crs, always_xy=True).transform
		else:
			self.output_crs = None
			self.output_transform = None
'''



def is_first_axis_east(crs):
	return crs.axis_info[0].direction.lower() == 'east'

def change_bbox_axis_order(bbox):
	""" Flip the axis order of the given bbox. """
	return [bbox[1], bbox[0], bbox[3], bbox[2]]


class CRS(object):

	def __init__(self, crs_code):
		self.crs_code = crs_code
		self.output_crs = None
		self.output_transform = None
		try:
			pyproj_crs = pyproj.CRS(self.crs_code)
			self.axis_info = pyproj_crs.axis_info
			self.to_epsg = pyproj_crs.to_epsg()

		except pyproj.exceptions.CRSError:
			assert self.crs_code == "CRS:84", "there is another crs code that pyproj.CRS cannot handle (apart from CRS:84): '{}'".format(self.crs_code)
			self.axis_info[0].direction = 'east'
			self.axis_info[0].unit_name = 'degree'
			self.to_epsg = "CRS:84"
