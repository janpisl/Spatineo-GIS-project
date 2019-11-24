from pyproj import Transformer
import logging
# logging levels = DEBUG, INFO, WARNING, ERROR, CRITICAL
import datetime
import xml.etree.ElementTree as ET

logging.basicConfig(filename=datetime.datetime.now().strftime("%d.%b_%Y_%H_%M_%S") + '.log', level=logging.INFO)



def transform_bbox(bbox, transform_from, transform_to):

	to_crs_84_flag = None
	from_crs_84_flag = None

	if transform_from == transform_to:
		logging.warning("we are trying to transform between two identical crs: {}".format(transform_to))
		return bbox

	if transform_to == "CRS:84":
		transform_to == "EPSG:4326"
		to_crs_84_flag = True



	if transform_from == "CRS:84":
		transform_from == "EPSG:4326"
		from_crs_84_flag = True		

	for projection in [transform_from, transform_to]:
		
		try:
			epsg, code = str(projection).split(":")
		except ValueError:
			code = projection
			epsg = "EPSG"


		#TODO: checking that code is int is not done like this
		assert epsg == "EPSG" and int(code)
		projection = epsg + ":" + str(code)
			

	tr = Transformer.from_crs(transform_from, transform_to)


	if transform_from == "EPSG:4326" and not from_crs_84_flag:
		transformed = tr.transform(bbox[1], bbox[0]) + tr.transform(bbox[3], bbox[2])
	else:
		transformed = tr.transform(bbox[0], bbox[1]) + tr.transform(bbox[2], bbox[3])

	if to_crs_84_flag:
		transformed = [transformed[1], transformed[0], transformed[3], transformed[2]]

	
	return transformed


def get_layer_bbox_wms(root, layer_name, crs):

	bbox = None
	
	epsg_code = crs.to_epsg()

	def get_ref_system(element): # local function for getting reference system for getCapabilities file
		try: 
			ref_system = element.attrib['CRS']
		except KeyError:
			try:
				ref_system = element.attrib['SRS']
			except KeyError:
				raise Exception("CRS not found in {}".format(element.attrib))
		return ref_system

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
						bbox = transform_bbox(bbox, get_ref_system(element), epsg_code)
					break
		return bbox
		

	elements = root.findall('{http://www.opengis.net/wms}Capability/{http://www.opengis.net/wms}Layer/{http://www.opengis.net/wms}Layer/{http://www.opengis.net/wms}Layer/') + root.findall('{http://www.opengis.net/wms}Capability/{http://www.opengis.net/wms}Layer/{http://www.opengis.net/wms}Layer/') + root.findall('{http://www.opengis.net/wms}Capability/{http://www.opengis.net/wms}Layer/') + root.findall('Capability/Layer/Layer/Layer/') + root.findall('Capability/Layer/') + root.findall('Capability/Layer/Layer/')

	bbox = search(elements, layer_name=layer_name, epsg_code=epsg_code)
	if bbox is None:
		bbox = search(elements, layer_name=layer_name, epsg_code=epsg_code, crs_flag = True)
		if bbox is None:
			bbox = search(elements, layer_name="not_required", epsg_code=epsg_code)
			if bbox is None:
				bbox = search(elements, layer_name="not_required", epsg_code=epsg_code, crs_flag = True)

	return bbox




def get_layer_bbox_wfs(root, layer_name, crs):

	bbox = None
	bbox0 = None
	layer = False

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
						raise Exception("Unexpected bbox value when parsing xml: {}. Expected LowerCorner or UpperCorner".format(elem.tag))	
				
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
							raise Exception("Unexpected bbox value when parsing xml: {}. Expected LowerCorner or UpperCorner".format(elem.tag))	
					bbox0 = lonlat1 + lonlat2
				layer = False


	# conversion of bbox0 (WGS84 to self.crs)
	if not bbox and bbox0:

		bbox = transform_bbox(bbox0, "EPSG:4326", crs.to_epsg())


	return bbox

def get_layer_bbox(path_to_capabl, layer_name, crs, service_type):

	root = ET.parse(path_to_capabl).getroot()
	bbox = None

	if service_type == 'WMS':
		
		bbox = get_layer_bbox_wms(root, layer_name, crs)

	elif service_type == 'WFS':

		bbox = get_layer_bbox_wfs(root, layer_name, crs)

	# throw exception if the bbox is not found
	if not bbox:
		raise Exception("Bounding box information not found for the layer.")
	
	logging.info("bbox: {}".format(bbox))

	return bbox

