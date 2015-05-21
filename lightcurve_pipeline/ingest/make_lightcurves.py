"""Create lightcurves
"""

import logging
import os

import lightcurve
from lightcurve_pipeline.database.database_interface import engine
from lightcurve_pipeline.database.database_interface import session
from lightcurve_pipeline.database.database_interface import Metadata
from lightcurve_pipeline.database.database_interface import Outputs
from lightcurve_pipeline.utils.utils import make_directory
from lightcurve_pipeline.utils.utils import SETTINGS
from lightcurve_pipeline.utils.utils import set_permissions

# -----------------------------------------------------------------------------

def make_composite_lightcurves():
    """Create composite lightcurves made up of datasets with similar
    targname, detector, opt_elem, and cenwave.  The lightcurves that
    require processing are determined by NULL composite_path values in
    the outputs table of the database.
    """

    logging.info('')
    logging.info('Creating composite lightcurves')

    # Create composite directory if it doesn't already exist
    make_directory(SETTINGS['composite_dir'])

    # Get list of datasets that need to be (re)processed by querying
    # for empty composite records
    datasets = session.query(Metadata.targname, Metadata.detector,
        Metadata.opt_elem, Metadata.cenwave).join(Outputs)\
        .filter(Outputs.composite_path == None).all()
    datasets = set(datasets)
    logging.info('{} datasets to process'.format(len(datasets)))

    for dataset in datasets:

        # Parse the dataset information
        targname = dataset[0]
        detector = dataset[1]
        opt_elem = dataset[2]
        cenwave = dataset[3]
        logging.info('')
        logging.info('Processing dataset: {}\t{}\t{}\t{}'.format(targname,
            detector, opt_elem, cenwave))

        # Get list of files for each dataset to be processed
        filelist = session.query(
            Metadata.id, Metadata.path, Metadata.filename)\
            .filter(Metadata.targname == dataset[0])\
            .filter(Metadata.detector == dataset[1])\
            .filter(Metadata.opt_elem == dataset[2])\
            .filter(Metadata.cenwave == dataset[3]).all()
        metadata_ids = [item[0] for item in filelist]
        files_to_process = [os.path.join(item[1], item[2]) for item in filelist]
        logging.info('\t{} file(s) to process.'.format(len(files_to_process)))

        # Perform the extraction
        logging.info('\tPerforming extraction.')
        path = SETTINGS['composite_dir']
        output_filename = '{}_{}_{}_{}_curve.fits'.format(targname, detector,
            opt_elem, cenwave)
        save_loc = os.path.join(path, output_filename)
        lightcurve.io.composite(files_to_process, save_loc)
        set_permissions(save_loc)
        logging.info('\tComposite lightcurve saved to {}'.format(save_loc))

        # Update the outputs table with the composite information
        logging.info('\tUpdating outputs table.')
        for metadata_id in metadata_ids:
            session.query(Outputs)\
                .filter(Outputs.metadata_id == metadata_id)\
                .update({'composite_path':path,
                    'composite_filename':output_filename})
        session.commit()

# -----------------------------------------------------------------------------

def make_individual_lightcurve(metadata_dict, outputs_dict):
    """Extract the spectra and create a lightcurve

    Parameters
    ----------
    metadata_dict : dict
        A dictionary containing metadata of the file.
    outputs_dict : dict
        A dictionary containing output product information.

    Returns
    -------
    success : bool
        True/False status of successful extraction

    """

    success = True

    # Create parent output directory if necessary
    make_directory(outputs_dict['individual_path'])

    # Create the lightcurve if it doesn't already exist
    outputname = os.path.join(outputs_dict['individual_path'],
        outputs_dict['individual_filename'])

    if not os.path.exists(outputname):
        inputname = os.path.join(SETTINGS['ingest_dir'],
            metadata_dict['filename'])

        logging.info('\tCreating lightcurve {}'.format(outputname))
        try:
            lc = lightcurve.open(filename=inputname, step=1)
            lc.write(outputname)
            set_permissions(outputname)
        except Exception as e:
            logging.warn('Exception raised for {}'.format(outputname))
            logging.warn('\t{}'.format(e.message))
            success = False

    return success