"""
This module contains functions that create lightcurves (in the form of
FITS tables) from both individual and composite datasets.  It is
essentially a wrapper around the ``lightcurve`` library, which makes
lightcurve objects, for example:

::

    lc = lightcurve.LightCurve(filename)

This module uses multiprocessing to process the composite lightcurves
over numerous cores, as given by the ``num_cores`` key in the config
file (see below).

**Authors:**

    Matthew Bourque

**Use:**

    This module is intended to be imported from the ``ingest_hstlc``
    script as such:

::

    from lightcurve_pipeline.ingest.make_lightcurves import make_composite_lightcurves
    from lightcurve_pipeline.ingest.make_lightcurves import make_individual_lightcurve

**Dependencies:**

    (1) Users must have access to the hstlc database
    (2) Users must also have a ``config.yaml`` file located in the
        ``lightcurve_pipeline/utils/`` directory with the following
        keys:

        - ``db_connection_string`` - The hstlc database connection
          string
        - ``ingest_dir`` - The path to where files to be ingested are
          stored
        - ``composite_dir`` - The path to where hstlc composite output
          products are stored
        - ``num_cores`` - The number of cores to use during
          multiprocessing

    Other external library dependencies include:
        - ``pymysql``
        - ``sqlalchemy``
        - ``lightcurve``
        - ``lightcurve_pipeline``
"""

import logging
import multiprocessing
import os
import traceback

import lightcurve

from lightcurve_pipeline.database.database_interface import get_session
from lightcurve_pipeline.database.database_interface import Metadata
from lightcurve_pipeline.database.database_interface import Outputs
from lightcurve_pipeline.utils.utils import make_directory
from lightcurve_pipeline.utils.utils import SETTINGS
from lightcurve_pipeline.utils.utils import set_permissions

# -----------------------------------------------------------------------------

def make_composite_lightcurves():
    """Create composite lightcurves made up of datasets with similar
    ``targname``, ``detector``, ``opt_elem``, ``cenwave``, and
    ``aperture``.  The lightcurves that require processing are
    determined by ``NULL`` ``composite_path`` values in the ``outputs``
    table of the database.
    """

    logging.info('')
    logging.info('Creating composite lightcurves')

    # Create composite directory if it doesn't already exist
    make_directory(SETTINGS['composite_dir'])

    # Get list of datasets that need to be (re)processed by querying
    # for empty composite records
    session = get_session()
    datasets = session.query(Metadata.instrume, Metadata.detector,
        Metadata.targname, Metadata.opt_elem, Metadata.cenwave,
        Metadata.aperture).join(Outputs)\
        .filter(Outputs.composite_path == None).all()
    datasets = set(datasets)
    session.close()

    # Process each dataset using multiprocessing
    logging.info('Creating {} composites using {} core(s)'.format(
        len(datasets), SETTINGS['num_cores']))
    logging.info('')
    pool = multiprocessing.Pool(processes=SETTINGS['num_cores'])
    pool.map(process_dataset, datasets)
    pool.close()
    pool.join()

# -----------------------------------------------------------------------------

def make_individual_lightcurve(metadata_dict, outputs_dict):
    """Create a lightcurve for an individual dataset

    Parameters
    ----------
    metadata_dict : dict
        A dictionary containing metadata of the file
    outputs_dict : dict
        A dictionary containing output product information

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

        try:
            lc = lightcurve.LightCurve(filename=inputname, step=2, verbosity=1)
            lc.write(outputname)
            set_permissions(outputname)
        except Exception as e:
            logging.warn('Exception raised for {}'.format(outputname))
            logging.warn('\t{}'.format(e.message))
            success = False

    return success

# -----------------------------------------------------------------------------

def process_dataset(dataset):
    """Create a composite lightcurve for the given dataset

    Parameters
    ----------
    dataset : list
        A list comprised of four elements.  The first element is the
        ``targname``, the second is the ``detector``, the third is the
        ``opt_elem``, and the fourth is the ``cenwave``.
    """

    try:

        # Parse the dataset information
        instrume = dataset[0]
        detector = dataset[1]
        targname = dataset[2]
        opt_elem = dataset[3]
        cenwave = dataset[4]
        aperture = dataset[5]

        # Get list of files for each dataset to be processed
        session = get_session()
        filelist = session.query(
            Metadata.id, Metadata.path, Metadata.filename)\
            .filter(Metadata.instrume == instrume)\
            .filter(Metadata.detector == detector)\
            .filter(Metadata.targname == targname)\
            .filter(Metadata.opt_elem == opt_elem)\
            .filter(Metadata.cenwave == cenwave)\
            .filter(Metadata.aperture == aperture).all()
        metadata_ids = [item[0] for item in filelist]
        files_to_process = [os.path.join(item[1], item[2]) for item in filelist]
        logging.info('Processing dataset: {}\t{}\t{}\t{}\t{}\t{}: {} files to process'.format(
            instrume, detector, targname, opt_elem, cenwave, aperture,
            len(files_to_process)))
        session.close()

        # Perform the extraction
        path = SETTINGS['composite_dir']
        output_filename = 'hlsp_hstlc_hst_{}-{}_{}_{}_{}_{}_v1_sci.fits'.format(
            instrume, detector, targname, opt_elem, cenwave, aperture).lower()
        save_loc = os.path.join(path, output_filename)
        lightcurve.composite(files_to_process, save_loc, step=2)
        set_permissions(save_loc)
        logging.info('\tComposite lightcurve saved to {}'.format(save_loc))

        # Update the outputs table with the composite information
        session = get_session()
        for metadata_id in metadata_ids:
            session.query(Outputs)\
                .filter(Outputs.metadata_id == metadata_id)\
                .update({'composite_path':path,
                    'composite_filename':output_filename})
        session.commit()
        session.close()

    # Track any errors that happen during processing
    except Exception as error:
        dataset_name = 'hlsp_hstlc_hst_{}-{}_{}_{}_{}_{}_curve.fits'.format(
            dataset[0], dataset[1], dataset[2], dataset[3], dataset[4],
            dataset[5])
        trace = 'Failed to create composite for dataset {}\n{}'.format(
            dataset_name, traceback.format_exc())
        logging.critical(trace)
