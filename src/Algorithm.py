

class Algorithm():
	def __init__(raster, responses, service):
		'''
		args:
			raster = empty raster
			data_file = a list of responses ('results' in the data file) for one layer key
			service = WMS/WFS
		'''	
		self.raster = raster
		self.responses = responses
		self.mode = mode
		


	def solve(self):
			for response in self.responses:
				'''
				what comes here:
				for all self.raster.pixels within response['bbox']:
					if response['imageAnalysisResult'] > 0:
						pixel.value += 1
					elif response['imageAnalysisResult'] == 0:
						pixel.value -= 1
					else:
						#invalid data.. go to next iteration 
						continue
				'''	

		return result




'''
        # Cut a raster by each  polygon in a shapefile and write to new raster
        ref_image_out = None
        with fiona.open("p04611r04611_sample_small_1_segmented.gpkg") as src:
            i = 0
            for feat in src:
                g = shape(feat['geometry'])
                ref_image, ref_transform = rasterio.mask.mask(img_input, [mapping(g)], crop=False)
                nd = img_input.nodata
                mask = ref_image[0] != nd
                avg = np.mean(ref_image[:, mask], axis=1)
                #ref_image[:,mask] = avg # I Could not get this line working...
                bands_out[0][mask] = avg[0]
                bands_out[1][mask] = avg[1]
                bands_out[2][mask] = avg[2]
                bands_out[3][mask] = avg[3]
                #if i == 1000:
                #    ref_image_out = ref_image
                i = i + 1
                print("Average val.: {}".format(avg))
            print("Number of segments: {}".format(i))
        
        # Save the image into disk.        
        img_output = rasterio.open(
            "p04611r04611_sample_small_out.tif",
            'w',
            driver='GTiff',
            compress='lzw',
            nodata=nd,
            height=h,
            width=w,
            count=4,
            dtype=rasterio.uint16,
            crs=img_input_crs,
            transform=transform,)   
        img_output.write(bands_out) # bands, ref_image_out
        img_output.close()
'''


''' in order not to have to create a gpkg we can just create features from bboxes. a feature looks like this:

{'type': 'Feature', 'id': '1', 'properties': OrderedDict([('segment_id', 993)]), 'geometry': {'type': 'MultiPolygon', 'coordinates': [[[(122632.5678, 6711534.6403), (122752.5678, 6711534.6403), (122752.5678, 6711524.6403), (122762.5678, 6711524.6403), (122762.5678, 6711514.6403), (122782.5678, 6711514.6403), (122782.5678, 6711484.6403), (122772.5678, 6711484.6403), (122772.5678, 6711454.6403), (122782.5678, 6711454.6403), (122782.5678, 6711424.6403), (122772.5678, 6711424.6403), (122772.5678, 6711444.6403), (122762.5678, 6711444.6403), (122762.5678, 6711454.6403), (122752.5678, 6711454.6403), (122752.5678, 6711464.6403), (122742.5678, 6711464.6403), (122742.5678, 6711494.6403), (122732.5678, 6711494.6403), (122732.5678, 6711504.6403), (122722.5678, 6711504.6403), (122722.5678, 6711524.6403), (122712.5678, 6711524.6403), (122712.5678, 6711514.6403), (122702.5678, 6711514.6403), (122662.5678, 6711514.6403), (122662.5678, 6711504.6403), (122652.5678, 6711504.6403), (122652.5678, 6711494.6403), (122642.5678, 6711494.6403), (122642.5678, 6711484.6403), (122632.5678, 6711484.6403), (122632.5678, 6711454.6403), (122622.5678, 6711454.6403), (122622.5678, 6711504.6403), (122632.5678, 6711504.6403), (122632.5678, 6711534.6403)]]]}}
'''