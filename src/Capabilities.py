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

		if "wms" in root.tag.lower():
			return 'WMS'

		for element in root:
				for child in element:
					if "wms" in child.text.lower():
						return 'WMS'

		if "wfs" in root.tag.lower():
			return 'WFS'

		raise Exception("Couldn't retrieve service type from {}".format(root.tag))
		

	def get_layer_bbox(self, layer_name, crs):
		''' The fuction parses the GetCapabilities XML document in order to search for a 'global' bbox to use. 
			It retrieves the bbox from the GetCapabilties document by finding the tag of the current request where it finds the bbox with correct CRS. 
			returns:
				bbox: bounding box (array) of the service
		'''
		# TODO: It must be able to do both WMS and WFS as well as work with different types of XML document setups.

		epsg_code = crs.get_epsg()

		if self.service_type == 'WMS':
			# WMS solution
			# init
			bbox = None
			layer = False

			# parsing the XML document to the the root (setup) of the document
			root = self.tree.getroot()

			elements = root.findall('{http://www.opengis.net/wms}Capability/{http://www.opengis.net/wms}Layer/{http://www.opengis.net/wms}Layer/{http://www.opengis.net/wms}Layer/') +root.findall('{http://www.opengis.net/wms}Capability/{http://www.opengis.net/wms}Layer/{http://www.opengis.net/wms}Layer/')

			# WMS version 1.1.1, 1.3.0
			# searching the XML document for the tag with the correct request name
			for element in elements:
				if (element.tag == '{http://www.opengis.net/wms}Name') and (element.text != layer_name):
					layer = False
				# change layer to true if the request is found
				if element.text == layer_name:
					layer = True


				# retrieve the bbox when the contraints are upheld
				if element.tag == '{http://www.opengis.net/wms}BoundingBox' and layer:

					try: 
						ref_system = element.attrib['CRS']
					except KeyError:
						try:
							ref_system = element.attrib['SRS']
						except KeyError:
							raise Exception("CRS not found in {}".format(element.attrib))


					if str(epsg_code) in ref_system:

						bbox = [element.attrib['minx'], element.attrib['miny'], element.attrib['maxx'], element.attrib['maxy']]

						# change from strings to float
						for item in range(len(bbox)):
							bbox[item] = float(bbox[item])
						
						# this is to stop the search when bbox is found. if not here, bbox values get overwritten by values from other layers
						break
				
			
			if not layer: 
				elements = root.findall('Capability/Layer/')
				print(elements)
				for element in elements:
					#print(element.text)
					#print(element.attrib)
					print(element.tag)
					if 'BoundingBox' in element.text:
						print(element.tag)
						print(element.attrib)

						try: 
							ref_system = element.attrib['CRS']
						except KeyError:
							try:
								ref_system = element.attrib['SRS']
							except KeyError:
								raise Exception("CRS not found in {}".format(element.attrib))
						print(ref_system)

						if str(epsg_code) in ref_system:

							bbox = [element.attrib['minx'], element.attrib['miny'], element.attrib['maxx'], element.attrib['maxy']]

							# change from strings to float
							for item in range(len(bbox)):
								bbox[item] = float(bbox[item])
								
							# this is to stop the search when bbox is found. if not here, bbox values get overwritten by values from other layers
							break
			


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

		print("bbox: {}".format(bbox))
		return bbox