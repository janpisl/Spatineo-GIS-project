"""batch.py

Automatizes the execution of the functionality in process.py for
multiple files within one folder. It requires a configuration file.

How to run:

        $ python3 batch.py batch.ini

"""

import glob
import logging
import datetime
import configparser
import argparse
import pdb
import signal
from pathlib import Path
from Process import Process
from Validate import validate

logging.basicConfig(filename="../../output_data/logs/" \
                    + datetime.datetime.now().strftime("%d.%b_%Y_%H_%M_%S") \
                    + '.log', level=logging.INFO)

def handler(signum, frame):
   logging.error ("validation took too long - terminated")
   raise Exception("validation took too long - terminated")



def run_batch(cfg):
    """For each file in folder given in configuration,
    generates a configuration file, creates an instance
    of the process.py class, runs algorithm which produces
    results and validates these results using the validate
    module.

    Parameters
    ----------
    cfg : ConfigParser object

    """

    directory = cfg.get('data', 'response_file')
    get_capabilities_docs = cfg.get('data', 'get_capabilities')
    output_dir = cfg.get('data', 'output_dir')
    input_first_axis_direction = cfg.get('input', 'first_axis_direction')
    resolution = cfg.get('result', 'resolution')
    output_crs = cfg.get('result', 'output_crs')
    output_first_axis_direction = cfg.get('result', 'first_axis_direction')
    max_raster_size = cfg.get('other', 'max_raster_size')
    max_features = cfg.get('other', 'max_features_for_validation')

    signal.signal(signal.SIGALRM, handler)

    for file_path in glob.glob(directory + '*.json'):
        file = Path(file_path).stem
        logging.info("file {} begins".format(file))

        config = configparser.ConfigParser()
        config.add_section('data')
        config.add_section('other')
        config.add_section('result')
        config.add_section('input')

        config.set('data', 'response_file', file_path)
        config.set('data', 'get_capabilities', get_capabilities_docs + file.split("_")[0] + ".xml")
        config.set('data', 'raster_output_path', output_dir + file + ".tif")

        config.set('data', 'output_dir', output_dir)
        config.set('data', 'raster_output_path', output_dir + file + ".tif")
        config.set('data', 'binary_raster_output_path', output_dir + "bin_" + file + ".tif")
        config.set('data', 'validation_raster_output_path', output_dir + "val_" + file + ".tif")
        config.set('input', 'first_axis_direction', input_first_axis_direction)
        config.set('result', 'resolution', resolution)
        config.set('result', 'output_crs', output_crs)
        config.set('result', 'first_axis_direction', output_first_axis_direction)
        config.set('other', 'max_raster_size', max_raster_size)
        config.set('other', 'max_features_for_validation', max_features)

        try:
            process = Process(config)
            process.run_algorithm()


            signal.alarm(180)
            try:
                # validation of the result.
                validate(process.url, process.layer_name, process.crs.crs_code,
                         process.layer_bbox, process.bin_raster_path,
                         process.val_raster_output_path, process.service_type,
                         process.service_version, process.max_features_for_validation,
                         process.flip_features, process.data_bounds, process.service)

            except Exception as e:
                print(e)
            signal.alarm(0)

            logging.info("File '{}' done. \n \n".format(file))
        except Exception as e:
            logging.info("File '{}' failed.\nError message: '{}' \n \n".format(file, e))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("path_to_config", help="Path to the file containing configuration.")
    args = parser.parse_args()

    config = configparser.ConfigParser()
    data = config.read(args.path_to_config)
    if len(data) == 0:
        raise Exception("Configuration file not found.")

    run_batch(config)
