"""Ingestion script to move files into hstlc filesystem and update the
hstlc database.
"""

import datetime
import getpass
import glob
import logging
import os
import shutil
import socket
import sys

import astropy
from astropy.io import fits
import lightcurve
import numpy
import sqlalchemy

from lightcurve_pipeline.settings.settings import SETTINGS
from lightcurve_pipeline.settings.settings import set_permissions
from lightcurve_pipeline.database.database_interface import engine
from lightcurve_pipeline.database.database_interface import session
from lightcurve_pipeline.database.database_interface import BadData
from lightcurve_pipeline.database.database_interface import Metadata
from lightcurve_pipeline.database.database_interface import Outputs

os.environ['lref'] = '/grp/hst/cdbs/lref/'

# -----------------------------------------------------------------------------

def composite(filelist, save_loc):
    """Creates a composite lightcurve from files in filelist and saves
    it to the save_loc.

    Parameters
    ----------
    filelist : list
        A list of full paths to the input files.
    save_loc : string
        The path to the location in which the composite lightcurve is
        saved.
    """

    pass

# -----------------------------------------------------------------------------

def ingest(filename, header):
    """Ingests the file into the hstlc filesystem and database. Also
    produces output lightcurves.

    Parameters
    ----------
    filename : string
        The absolute path to the file.
    header : astropy.io.fits.header.Header
        The primary header of the file.
    """

    metadata_dict, outputs_dict = make_file_dicts(filename, header)
    update_metadata_table(metadata_dict)

    success = make_lightcurve(metadata_dict, outputs_dict)
    if success:
        update_outputs_table(metadata_dict, outputs_dict)
        make_quicklook(outputs_dict)

    move_file(metadata_dict)

# -----------------------------------------------------------------------------

def insert_or_update(table, data, id_num):
    """
    Insert or update the table with information in the record_dict.

    Parameters
    ----------
    table :
        The table of the database to update.
    data : dict
        A dictionary of the information to update.  Each key of the
        dictionary must be a column in the Table.
    id_num : string
        The row ID to update.  If id_test is blank, then a new row is
        inserted.
    """

    if id_num == '':
        engine.execute(table.__table__.insert(), data)
    else:
        session.query(table)\
            .filter(table.id == id_num)\
            .update(data)

# -----------------------------------------------------------------------------

def make_composite_lightcurves():
    """Create composite lightcurves made up of datasets with similar
    targname, detector, opt_elem, and cenwave.  The lightcurves that
    require processing are determined by NULL composite_path values in
    the outputs table of the database.
    """

    logging.info('')
    logging.info('Creating composite lightcurves')

    # Get list of datasets that need to be (re)processed by querying
    # for empty composite records
    query = session.query(Metadata.targname, Metadata.detector,
        Metadata.opt_elem, Metadata.cenwave)\
        .join(Outputs).filter(Outputs.composite_path == 'NULL').all()
    datasets = set(query)
    logging.info('{} datasets to process'.format(len(datasets)))

    # Make composite lightcurves of datasets that need (re)processing
    for dataset in datasets:

        # Parse the dataset parameters
        targname = dataset[0]
        detector = dataset[1]
        opt_elem = dataset[2]
        cenwave = dataset[3]

        logging.info('')
        logging.info('Processing dataset: {}\t{}\t{}\t{}'.format(targname,
            detector, opt_elem, cenwave))

        # Query for the individual filenames in each dataset
        files = session.query(Metadata.filename, Metadata.path)\
            .filter(Metadata.targname == targname)\
            .filter(Metadata.detector == detector)\
            .filter(Metadata.opt_elem == opt_elem)\
            .filter(Metadata.cenwave == cenwave).all()

        # Parse the individual files
        files_to_process = [os.path.join(item[0], item[1]) for item in files]
        logging.info('\t{} files to process.'.format(len(files_to_process)))

        # Perform the extraction
        logging.info('\tPerforming extraction.')
        path = SETTINGS['composite_dir']
        filename = '{}_{}_{}_{}_curve.fits'.format(targname, detector,
            opt_elem, cenwave)
        save_loc = os.path.join(path, filename)
        composite_lc = composite(files_to_process, save_loc)
        logging.info('\tComposite lightcurve saved to {}'.format(save_loc))

        # Update the outputs table with the composite information
        logging.info('\tUpdating outputs table.')
        session.query(Outputs).join(Metadata)\
            .filter(Metadata.targname == targname)\
            .filter(Metadata.detector == detector)\
            .filter(Metadata.opt_elem == opt_elem)\
            .filter(Metadata.cenwave == cenwave)\
            .update({'composite_path':path, 'composite_filename':filename})

# -----------------------------------------------------------------------------

def make_directory(directory):
    """Create a directory if it doesn't already exist and set the
    permissions.

    Parameters
    ----------
    directory : string
        The path to the directory.
    """

    if not os.path.exists(directory):
        logging.info('\tCreating directory {}'.format(directory))
        os.mkdir(directory)
        set_permissions(directory)

# -----------------------------------------------------------------------------

def make_file_dicts(filename, header):
    """Return a dictionary containing file metadata and a dictionary
    containing output product information

    Parameters
    ----------
    filename : string
        The absolute path to the file.
    header : astropy.io.fits.header.Header
        The primary header of the file.

    Returns
    -------
    metadata_dict : dict
        A dictionary containing metadata of the file.
    outputs_dict : dict
        A dictionary containing output product information.
    """

    metadata_dict = {}
    outputs_dict = {}

    # Set header keys
    metadata_dict['telescop'] = header['TELESCOP']
    metadata_dict['instrume'] = header['INSTRUME']
    metadata_dict['targname'] = header['TARGNAME']
    metadata_dict['cal_ver'] = header['CAL_VER']
    metadata_dict['obstype'] = header['OBSTYPE']
    metadata_dict['aperture'] = header['APERTURE']
    metadata_dict['detector'] = header['DETECTOR']
    metadata_dict['opt_elem'] = header['OPT_ELEM']

    if header['OBSTYPE'] == 'SPECTROSCOPIC':
        metadata_dict['cenwave'] = header['CENWAVE']
    elif header['OBSTYPE'] == 'IMAGING':
        metadata_dict['cenwave'] = 0

    if header['INSTRUME'] == 'COS':
        metadata_dict['fppos'] = header['FPPOS']
    elif header['INSTRUME'] == 'STIS':
        metadata_dict['fppos'] = 0

    # Set image metadata keys
    metadata_dict['filename'] = os.path.basename(filename)
    metadata_dict['path'] = os.path.join(SETTINGS['filesystem_dir'],
        metadata_dict['targname'])
    metadata_dict['ingest_date'] = datetime.datetime.strftime(
        datetime.datetime.today(), '%Y-%m-%d')

    # Set outputs keys
    outputs_dict['individual_path'] = \
        metadata_dict['path'].replace('filesystem', 'outputs')
    outputs_dict['individual_filename'] = \
        '{}_curve.fits'.format(metadata_dict['filename'].split('_')[0])

    return metadata_dict, outputs_dict

# -----------------------------------------------------------------------------

def make_lightcurve(metadata_dict, outputs_dict):
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

# -----------------------------------------------------------------------------

def make_quicklook(outputs_dict):
    """Make a quicklook PNG of the lightcurve.

    Parameters
    ----------
    outputs_dict : dict
        A dictionary containing output product information.
    """

    lc_name = os.path.join(outputs_dict['individual_path'],
        outputs_dict['individual_filename'])
    logging.info('\tCreating quicklook plot.')
    lightcurve.io.quicklook(lc_name)
    set_permissions(lc_name.replace('.fits', '.png'))

# -----------------------------------------------------------------------------

def move_file(metadata_dict):
    """Move the file from the ingest directory into the filesystem.

    Parameters
    ----------
    metadata_dict : dict
        A dictionary containing metadata of the file.

    Notes
    -----
    The parent directory to the file is named afer the file's TARGNAME.
    """

    # Create parent directory if necessary
    make_directory(metadata_dict['path'])

    # Move the file from ingest directory into filesystem
    src = os.path.join(SETTINGS['ingest_dir'], metadata_dict['filename'])
    dst = os.path.join(metadata_dict['path'], metadata_dict['filename'])
    logging.info('\tMoving file.')
    if os.path.exists(dst):
        os.remove(dst)
    shutil.move(src, dst)

# -----------------------------------------------------------------------------

def setup_logging():
    """
    Configures and initializes a log to store program execution
    information.
    """

    # Configure logging
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M')
    module = os.path.basename(__file__).strip('.py')
    filename = '{}_{}.log'.format(module, timestamp)
    logfile = os.path.join(SETTINGS['log_dir'], filename)
    logging.basicConfig(
        filename=logfile,
        format='%(asctime)s %(levelname)s: %(message)s',
        datefmt='%m/%d/%Y %H:%M:%S',
        level=logging.INFO)

    # Log environment information
    logging.info('User: {}'.format(getpass.getuser()))
    logging.info('System: {}'.format(socket.gethostname()))
    logging.info('Python Version: {}'.format(sys.version.replace('\n', '')))
    logging.info('Python Path: {}'.format(sys.executable))
    logging.info('Numpy Version: {}'.format(numpy.__version__))
    logging.info('Numpy Path: {}'.format(numpy.__path__[0]))
    logging.info('Astropy Version: {}'.format(astropy.__version__))
    logging.info('Astropy Path: {}'.format(astropy.__path__[0]))
    logging.info('SQLAlchemy Version: {}'.format(sqlalchemy.__version__))
    logging.info('SQLAlchemy Path: {}'.format(sqlalchemy.__path__[0]))

    set_permissions(logfile)

# -----------------------------------------------------------------------------

def update_bad_data_table(filename, reason):
    """Insert or update a record pertaining to the filename in the
    bad_data table.

    Parameters
    ----------
    filename : string
        The filename of the file.
    reason : string
        The reason that the data is bad. Can either be 'No events' or
        'Bad EXPFLAG'.
    """

    # Build dictionary containing data to store
    bad_data_dict = {}
    bad_data_dict['filename'] = filename
    bad_data_dict['ingest_date'] = datetime.datetime.strftime(
        datetime.datetime.today(), '%Y-%m-%d')
    bad_data_dict['reason'] = reason

    # The the id of the record, if it exists
    query = session.query(BadData.id)\
        .filter(BadData.filename == filename).all()
    if query == []:
        id_num = ''
    else:
        id_num = query[0][0]

    # If id doesn't exist then instert.  If id exists, then update
    insert_or_update(BadData, bad_data_dict, id_num)

# -----------------------------------------------------------------------------

def update_metadata_table(metadata_dict):
    """Insert or update a record in the metadata table containing the
    metadata_dict information.

    Parameters
    ----------
    metadata_dict : dict
        A dictionary containing metadata of the file.  Each key of the
        metadata_dict corresponds to a column in the matadata table of the
        database.
    """

    logging.info('\tUpdating metadata table.')

    # Get the id of the record, if it exists
    query = session.query(Metadata.id)\
        .filter(Metadata.filename == metadata_dict['filename']).all()
    if query == []:
        id_num = ''
    else:
        id_num = query[0][0]

    # If id doesn't exist then insert. If id exsits, then update
    insert_or_update(Metadata, metadata_dict, id_num)

# -----------------------------------------------------------------------------

def update_outputs_table(metadata_dict, outputs_dict):
    """Insert or update a record in the outputs table containing
    output product information.

    Parameters
    ----------
    metadata_dict : dict
        A dictionary containing metadata of the file.
    outputs_dict : dict
        A dictionary containing output product information.
    """

    logging.info('\tUpdating outputs table.')

    # Get the metadata_id
    session.rollback()
    metadata_id_query = session.query(Metadata.id)\
        .filter(Metadata.filename == metadata_dict['filename']).all()
    metadata_id = metadata_id_query[0][0]
    outputs_dict['metadata_id'] = metadata_id

    # Get the id of the outputs record, if it exists
    id_query = session.query(Outputs.id)\
        .join(Metadata)\
        .filter(Metadata.filename == metadata_dict['filename']).all()
    if id_query == []:
        id_num = ''
    else:
        id_num = id_query[0][0]

    # If id doesn't exist then insert. If id exsits, then update
    insert_or_update(Outputs, outputs_dict, id_num)

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

if __name__ == '__main__':

    setup_logging()
    filelist = glob.glob(os.path.join(SETTINGS['ingest_dir'], '*.fits*'))

    for file_to_ingest in filelist:

        logging.info('')
        logging.info('Ingesting {}'.format(file_to_ingest))

        # Open file
        with fits.open(file_to_ingest, 'readonly') as hdulist:
            header = hdulist[0].header

            # Check that file has events and has NORMAL expflag
            if len(hdulist[1].data) == 0:
                update_bad_data_table(
                    os.path.basename(file_to_ingest),
                    'No events')
                logging.info('\tNo events, removing file')
                os.remove(file_to_ingest)

            elif hdulist[1].header['EXPFLAG'] != 'NORMAL':
                update_bad_data_table(
                    os.path.basename(file_to_ingest),
                    'Bad EXPFLAG')
                logging.info('\tBad EXPFLAG, removing file')
                os.remove(file_to_ingest)

            # Ingest the data if it is normal
            else:
                ingest(file_to_ingest, header)

    # Make composite lightcurves
    make_composite_lightcurves()
