import requests
import pdb
from PIL import Image
import io
import numpy as np


image = requests.get("http://paikkatieto.ymparisto.fi/arcgis/services/INSPIRE/SYKE_Hydrografia/MapServer/WmsServer?VERSION=1.3.0&SERVICE=WMS&REQUEST=GetMap&LAYERS=HY.Network.WatercourseLink&STYLES=&CRS=EPSG:3067&BBOX=353484.39290249243,6952336.504877807,515662.8104318712,7114514.922407186&WIDTH=256&HEIGHT=256&FORMAT=image/png&EXCEPTIONS=XML")


image = np.array(Image.open(io.BytesIO(image.content))) 


def test_pixel(image):

	for i in range(image.shape[0]):
		for j in range(image.shape[1]):
			try:
				if not np.array_equal(image[i][j], first_val):
					return True
			except UnboundLocalError:
				first_val = image[i][j]
	
	return False




#if (height % 3 == 0): megapixel_height
def test_for_var(image):
	data_grid = np.empty([3,3])
	size = round(image.shape[0]/data_grid.shape[0])
	#pdb.set_trace()
	for m in range(3):
		for k in range(3):
			image_subset = image[m*size:(m+1)*size,k*size:(k+1)*size,:]
			data_grid[m][k] = test_pixel(image_subset)

	return data_grid


print(test_for_var(image))

'''
from owslib.wms import WebMapService
wms = WebMapService("http://paikkatieto.ymparisto.fi/arcgis/services/INSPIRE/SYKE_Hydrografia/MapServer/WmsServer", version='1.3.0')

img = wms.getmap(layers=['HY.Network.WatercourseLink'],
					styles=[],
					srs='EPSG:3067',
					bbox=(353484.39290249243,6952336.504877807,515662.8104318712,7114514.922407186),
					size=(256, 256),
					format='image/png',
					transparent=False
					)
out = open('jpl_mosaic_visb.jpg', 'wb')
out.write(img.read())
out.close()

'''