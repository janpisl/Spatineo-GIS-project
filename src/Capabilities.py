import xml.etree.ElementTree as ET
from pyproj import Transformer
import logging
# logging levels = DEBUG, INFO, WARNING, ERROR, CRITICAL
import datetime
logging.basicConfig(filename=datetime.datetime.now().strftime("%d.%b_%Y_%H_%M_%S") + '.log', level=logging.INFO)

class Capabilities():

	def __init__(self, file_path, layer_name, crs):
		self.tree = ET.parse(file_path)
		self.service_type = self._get_service()
		self.bbox = self.get_layer_bbox(layer_name, crs)

	def _get_service(self):
		root = self.tree.getroot()
		service = None

		if "wms" in root.tag.lower():
			service = 'WMS'

		elif "wfs" in root.tag.lower():
			service = 'WFS'

		else:
			for element in root:
				for child in element:
					if "wms" in child.text.lower():
						return 'WMS'
					elif "wfs" in child.text.lower():
						return "WFS"

		if service is None:
			raise Exception("Couldn't retrieve service type from {}".format(root.tag))
		
		return service



	def get_layer_bbox_wms(self, layer_name, crs):

		bbox = None
		epsg_code = crs.get_epsg()

		def get_ref_system(element): # local function for getting reference system for getCapabilities file
			try: 
				ref_system = element.attrib['CRS']
			except KeyError:
				try:
					ref_system = element.attrib['SRS']
				except KeyError:
					raise Exception("CRS not found in {}".format(element.attrib))
			return ref_system


		def transform(bbox, transform_from, transform_to):
			tr = Transformer.from_crs(transform_from, "EPSG:" + transform_to)
			return tr.transform(bbox[0], bbox[1]) + tr.transform(bbox[2], bbox[3])


		def search(elements, layer_name, epsg_code, crs_flag=False):
			
			bbox = None
			if layer_name  == "not_required":
				layer = True
			else:
				layer = False

			for element in elements:
				if layer is False:
					layer = element.text == layer_name

				if (element.tag == '{http://www.opengis.net/wms}BoundingBox' or element.tag == 'BoundingBox') and layer:
					if (str(epsg_code) in get_ref_system(element)) or crs_flag is True:
						bbox = [float(i) for i in [element.attrib['minx'], element.attrib['miny'], element.attrib['maxx'], element.attrib['maxy']]]
						if crs_flag is True:
							bbox = transform(bbox_to_tranform, get_ref_system(element), epsg_code)
						break
			return bbox
			

		root = self.tree.getroot()

		elements = root.findall('{http://www.opengis.net/wms}Capability/{http://www.opengis.net/wms}Layer/{http://www.opengis.net/wms}Layer/{http://www.opengis.net/wms}Layer/') + root.findall('{http://www.opengis.net/wms}Capability/{http://www.opengis.net/wms}Layer/{http://www.opengis.net/wms}Layer/') + root.findall('{http://www.opengis.net/wms}Capability/{http://www.opengis.net/wms}Layer/') + root.findall('Capability/Layer/Layer/Layer/') + root.findall('Capability/Layer/') + root.findall('Capability/Layer/Layer/')

		bbox = search(elements, layer_name=layer_name, epsg_code=epsg_code)
		if bbox is None:
			bbox = search(elements, layer_name=layer_name, epsg_code=epsg_code, crs_flag = True)
			if bbox is None:
				bbox = search(elements, layer_name="not_required", epsg_code=epsg_code)
				if bbox is None:
					bbox = search(elements, layer_name="not_required", epsg_code=epsg_code, crs_flag = True)

		return bbox

	def get_layer_bbox(self, layer_name, crs):

		if self.service_type == 'WMS':
			
			bbox = self.get_layer_bbox_wms(layer_name, crs)

		elif self.service_type == 'WFS':

			# init
			bbox = None
			bbox0 = None
			layer = False

			# parsing the XML document to the root (setup) of the document
			root = self.tree.getroot()

			#WFS ver. 2.x.x
			for elem in root.findall('./{http://www.opengis.net/wfs/2.0}FeatureTypeList/{http://www.opengis.net/wfs/2.0}FeatureType'):
				for child in elem:
					if child.text:
						if ":" in child.text:
							layer_string = child.text.split(":")[1]
					if child.tag == '{http://www.opengis.net/wfs/2.0}Name' and (child.text in layer_name or layer_string in layer_name):
						layer = True

					if layer and (child.tag == '{http://www.opengis.net/ows/1.1}WGS84BoundingBox'):

						for elem in child:
							if "LowerCorner" in elem.tag:
								lonlat1 = elem.text.split()
								lonlat1 = [float(i) for i in lonlat1]
							elif "UpperCorner" in elem.tag:
								lonlat2 = elem.text.split() 
								lonlat2 = [float(i) for i in lonlat2]	
							else:
								raise Exception("Unexpected bbox value when parsing xml: {}. Expected LowerCorner or UpperCorner".format(element.tag))	
						
						bbox0 = lonlat1 + lonlat2
						layer = False
						break


			#WFS ver. 1.x.x (1.0.x, 1.1.x)
			for elem in root.findall('./{http://www.opengis.net/wfs}FeatureTypeList/{http://www.opengis.net/wfs}FeatureType'):
				for child in elem:
					if child.text:
						if ':' in child.text:
							layer_string = child.text.split(':')[1]
					if child.tag == '{http://www.opengis.net/wfs}Name'  and (child.text in layer_name or layer_string in layer_name):
						layer = True

					if layer and (child.tag == '{http://www.opengis.net/ows}WGS84BoundingBox' or child.tag == '{http://www.opengis.net/wfs}LatLongBoundingBox'):

						if child.tag == '{http://www.opengis.net/wfs}LatLongBoundingBox':
							bbox=[child.attrib['minx'], child.attrib['miny'], child.attrib['maxx'], child.attrib['maxy']]
							for i in range(len(bbox)):
								bbox[i]=float(bbox[i])
						else:
							for elem in child.getchildren():
								if "LowerCorner" in elem.tag:
									lonlat1 = elem.text.split()
									lonlat1 = [float(i) for i in lonlat1]
								elif "UpperCorner" in elem.tag:
									lonlat2 = elem.text.split() 
									lonlat2 = [float(i) for i in lonlat2]	
								else:
									raise Exception("Unexpected bbox value when parsing xml: {}. Expected LowerCorner or UpperCorner".format(element.tag))	
							bbox0 = lonlat1 + lonlat2
						layer = False


			# conversion of bbox0 (WGS84 to self.crs)
			if not bbox and bbox0:
				x1, y1 = crs.convert_from_wgs84(bbox0[0], bbox0[1])
				x2, y2 = crs.convert_from_wgs84(bbox0[2], bbox0[3])
				bbox = [x1,y1,x2,y2]

		# throw exception if the bbox is not found
		if not bbox:
			raise Exception("Bounding box information not found for the layer.")
		
		logging.info("bbox: {}".format(bbox))
		return bbox






