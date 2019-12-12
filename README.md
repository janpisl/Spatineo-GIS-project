# Spatineo-GIS-project
GIS software development project for Spatineo Oy done as a part of the Project Course at Aalto University by: 
* Jan Pisl
* Juho Hanninen
* Renée Mie Fredensborg Hansen 
* Lucie Stara

The program takes monitoring results of spatial services as input and calculates more precise location of the spatial data than the bounding box information given in the service's Capabilities.xml document. The program works with WMS and WFS services.

## General

### General workflow

The general workflow how the program works is visible in the following picture.

![General workflow diagram](/images/general_diagram.png)

In the view of the algorithm, the steps are following.

1. The input monitoring file contains thousands monitoring requests. They are converted to GeoJson-like python objects. 
2. Empty raster is created by the bounding box of the layer in certain resolution.
3. All requests are compared to the raster, and for each pixel all positive and negative results are counted.
4. Using the proportion of the negative results, pixels are interpreted as non-data or data ares.
5. Binary raster is smoothed, converted to the vector format and the final result is simplified and validated.

### File structure
All source code files are in [src](/src) directory. Example configuration files are provided in [sample_data](/sample_data).

The source code consists of 9 modules. Here are short descriptions of the modules. More documentation of the content of modules and their functions can be found in the code.

[**Process.py**](src/Process.py) - The module to call when running the program for a single file. Contains the class that initializes all needed values for the program.

[**Batch.py**](src/Batch.py) - The module to call when running batch process. Calls Process.py for all input files in the configured directory.

[**Algorithm.py**](src/Algorithm.py) - Contains the algorithm to calculate the analysis.

[**Capabilities.py**](src/Capabilities.py) - Contains functions to parse needed information from Capabilities.xml files.

[**InputData.py**](src/InputData.py) - Contains funtions to parse data from input monitoring result file. E.g. converts all requests in geojson-like objects for the analysis.

[**Projection.py**](src/Projection.py) - Contains a class to handle all coordinate reference system information with pyproj library.

[**ResultData.py**](src/ResultData.py) - Contains functions to create output files.

[**Validate.py**](src/Validate.py) - Contains functions to validate results of WMS and WFS services.

[**Compare.py**](src/Compare.py) - A draft to generate QGIS project file which shows the results. Not used by program. See [future development](#qgis-validation).



## Requirements and installation

### Python
This program runs on Python 3. (Developed on Python 3.7.) It can installed e.g. via the official website https://www.python.org. In many Linux distributions Python3 is pre-installed.

### GDAL
Python packages Fiona and Rasterio use [GDAL](https://gdal.org/index.html), which should be installed separately. GDAL installation is really different depending on the environment, so no general tips can be given. On Debian based Linux distributions, it's possible to install GDAL via apt - package manager.
```sh
sudo apt-get install gdal-bin
```
NOTE! Preferrably use GDAL 2.4 (or lower). Do not use GDAL 3.0 or greater, before updating Fiona and Rasterio!

### Python packages
All required Python packages are listed on [requirements.txt](requirements.txt) -file. They can be installed using [pip](https://pip.pypa.io/en/stable/quickstart/). Pip should be installed alongside Python, so it's not needed to install that separately.

Install required packages:
```sh
pip install -r requirements.txt
```

*Note: Depending on the Python versions installed on your machine, you may need to add number 3 after the command to indicate you're using Python3 -environment. (`python` -> `python3` and `pip` -> `pip3`). Especially on macOS and Linux*

### Folder creation
The output location for the logs is not moved to configuration, so the output folder should be configured manually.

```sh
mkdir ../output_data
mkdir ../output_data/logs
```

See [future development of logging](#logging).


## Input data

The program wants two input files for each service, monitoring result file and Capabilities.xml of the service. Capabilites.xml should follow the specification of the WMS/WFS standard.

Monitoring input file should be in JSON format and respect the following schema:
```json
{
    "layerKey": {
        "crs": "CRS code used in monitoring queries",
        "layerName": "Name of the monitored layer"
    },
    "results": [
        {
            "testResult": "The response status of the monitor request. 0 means valid response.",
            "imageAnalysisResult": "The analysis result of data existence. 1 means data, 0 means no data.",
            "bBox": "Bounding box (string) of the request.",
            "url" : "Url of the monitoring request."
        }
    ]
}
```
Additional attributes can be used. The example file could look like this:

```json
{
    "day": 20190328,
    "layerKey": {
        "crs": "EPSG:3067",
        "WMSServiceID": 13451,
        "layerName": "pnr:Paikka"
    },
    "results": [
        {
            "testResult": 0,
            "requestTime": 1553731309383,
            "imageAnalysisResult": 0,
            "bBox": "363842.66977658594,7039057.110498036,367128.1562129861,7042342.596934437",
            "url": "https://ws.nls.fi/nimisto/wfs?SERVICE=WFS&REQUEST=GetFeature&VERSION=1.1.0&MAXFEATURES=3&SRSNAME=EPSG:3067&TYPENAME=pnr:Paikka&BBOX=363842.66977658594,7039057.110498036,367128.1562129861,7042342.596934437"
        },
        ...
    ]
}
```

## Running the program

It's possible to run the program for one file or as a batch process for multiple files. The initialization is almost the same for both cases. Only difference is how to give input data. For a single file process the configuration needs one specific file of monitoring results and Capabilities.xml file related to that service. In a batch process a directory of monitoring input files and a directory of Capabities.xml files are configured. **Monitoring result file and Capabilies.xml file are combined by the file name. The first part of monitoring result file before `_` -character should match!** E.g. `5_HY.PhysicalWaters.Catchments.RiverBasin.json` and `5.xml` will be matched together.


### Configuration
First create a configuration file in .ini format.

The configuration should have following variables:

`[data]`
- `response_file`: Path to the file (Process.py) or directory (Batch.py) containing monitoring results. 
- `get_capabilities`: Path to the GetCapabilities-response file (Process.py) or directory (Batch.py). 
- `output_dir`: Directory where the output data will be placed.

`[input]`
- `first_axis_direction`: Define the first axis direction for input data. Options: `east`, `north`, `epsg` (pyproj database), `auto` (guess from the service). Prefer `auto` option.

`[result]`
- `resolution`: Resolution with which the analysis is done (in meters)
- `output_crs`: Output coordinate reference system (EPSG-code)
- `first_axis_direction`: Define the first axis direction for output data. Options: `east`, `epsg` (pyproj database). Prefer `east` option, because GIS softwares are usually not awared of north first order even with geographic coordinates.

`[other]`
- `max_features_for_validation`: Used for WFS validation. If number of features in a layer used for validation exceeds the limit, validation is skipped. If not set, validation is performed regardless of the feature count.
- `max_raster_size`: Maximum size of the raster file in pixels. If this value is exceeded, resolution decreases to meet the requirement. **This is crucial for the program runtime.**

See the example files [process_config.ini](sample_data/process_config.ini) and [batch_config.ini](batch/process_config.ini).


### Running

Call the script depending on the single file process or batch process.

For single file process:
```sh
cd src
python Process.py <path to config file>
```

For batch process:
```sh
cd src
python Batch.py <path to config file>
```
Depending on the file and service, the analysis takes something from tens of seconds to a couple of minutes. (With about 50000 requests.) The most time consuming part in the algorithm is masking requests to the empty raster created by the layer bounding box. To speed up process, increase the resolution. Also validation might take time depending on the service.

## Output files

### Result
The result consists of three files with the prefix `bin_`. 
- `.tif` file is the raster file of the analysis in binary format. 1 means data and 0 means non-data area.
- `.geojson` and `.gpkg` files contain the smoothed and simplified result in vector format. Geopackage file is computationally more efficient and advance (could be configured to contain multiple results in one file) but it takes more space especially for one service. GeoJSON file is human-readable and usually smaller, but could be not so widely supported and fail with complex geometries. The schema contains url, layer name, used resolution. The vector output can be modified in [ResultData.py](/src/ResultData.py) module.

### Validation
Validation consists of `val_*.tif` files and `.csv` summary file. Validation is made against the data provided by the server. In WFS services all features are fetched from the server and masked over the result. In WMS map image is asked from the server, image is analysed in the same way than the image analysis of monitoring service works, and results are combined to each other.
In validation raster 0 means right analysis, -1 (or 255 in uint8) false negative and 1 false positive result.
Validation results are summarized by the layer in csv file.

### Logs
Logs are generated in `../output_data/logs/` directory. Logging levels can be configured in the beginning of the each module.


## Known issues and future development

### Problem with border areas
Because there're always less requests in the border areas of the bounding box, the analysis sometimes fails there giving false positive areas.

### Coordinate reference system problems
Spatial services are configured sometimes against the standards, and the axis order might be different. Especially there're problems with services where first axis could be pointing north. (Usually geographic coordinates given in degrees.) There's possibility to configure direction manually, and in addition there's one automatic axis flipping if requests don't seem to be inside the bounding box area. Unfortunately, the current implementation might not work right with all possible cases.

### tmp.tif creation
Because rasterio can't be used without existing file, empty `tmp.tif` file is always created in the output data directory. It should be moved to use Python's tempfile module or removed after process.

### Automatic validation with WMS
The validation is not working very robust with WMS services. First of all, validation resolution is rough, because it's not wise to send very many queries, for example for every pixes. Secondly the service might send just a blank image which makes validation impossible.

### Logging
Logging output directory and level should be moved to configuration file instead of hard-coded paths. Logging could be also moved to use Logger-objects so that there won't be need for init logging in every file separately.

### QGIS validation
There's a draft to generate QGIS project file to compare easily the result and the actual data in [Compare.py](/src/Compare.py). The current implementation went too complicated. The better approach would be to use some xml template and fill the required fields with the information from the process.