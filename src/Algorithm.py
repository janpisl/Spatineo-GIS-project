

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

